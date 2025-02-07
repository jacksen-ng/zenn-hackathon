from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, BackgroundTasks, Request, status, Response, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import uvicorn
import models, schemas, crud
from database import engine, Base, get_db
import logging
from pdf_to_text import pdf_to_text
import io
from typing import Optional, AsyncGenerator, List
from gemini import gemini_chat, clear_conversation_memory
from starlette.middleware.base import BaseHTTPMiddleware
from utils.conversation_manager import conversation_manager
from datetime import datetime, timedelta
import os
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
import jwt_utils
from jwt_utils import create_access_token, get_current_user, get_current_active_user, ACCESS_TOKEN_EXPIRE_MINUTES, authenticate_user
from jwt import ExpiredSignatureError, InvalidTokenError
from starlette.middleware.sessions import SessionMiddleware
import secrets
from models import User  
import crud 
import schemas 
from crud import create_document, get_document_by_id, get_document_by_user  # 使用已定义的存储函数
from schemas import DocumentCreate, DocumentResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="AI チャットアシスタント",
    description="AI チャットアシスタント API ドキュメント",
    version="1.0.0"
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


FILE_SIZE_LIMIT = 2 * 1024 * 1024  

app.add_middleware(
    SessionMiddleware,
    secret_key=secrets.token_urlsafe(32),
    session_cookie="session",
    max_age=1800,  
    same_site="lax",
    https_only=False 
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as e:
            logger.error(f"Unhandled error: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={
                    "detail": f"Internal server error: {str(e)}",
                    "success": False
                }
            )

app.add_middleware(ErrorHandlingMiddleware)

templates = Jinja2Templates(directory="templates")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

#@app.get("/", response_class=HTMLResponse)
#async def read_root(request: Request):
#    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/users", response_model=schemas.UserResponse)
async def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = await crud.create_user(db=db, user=user)
    return schemas.UserResponse(
        id=db_user.id,
        email=db_user.email,
        success=True
    )

@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = await create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/api/login", response_model=schemas.UserResponse)
async def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    try:
        user = await jwt_utils.authenticate_user(db, form_data.username, form_data.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="メールアドレスまたはパスワードが正しくありません"
            )
        
        access_token = jwt_utils.create_access_token(data={"sub": user.email})
        
        conversations = await crud.get_user_conversations(db, user.id)
        
        if not conversations:
            new_conversation = await crud.create_conversation(
                db=db,
                user_id=user.id,
                title=f"新しいチャット {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            conversation_id = new_conversation.id
        else:
            conversation_id = conversations[0].id
        
        request.session["user_id"] = user.id
        request.session["email"] = user.email
        
        return schemas.UserResponse(
            id=user.id,
            email=user.email,
            success=True,
            token=access_token,
            conversation_id=conversation_id 
        )
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
        
@app.post("/api/signup", response_model=schemas.UserResponse)
async def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    logger.info(f"Signup attempt for email: {user.email}")
    try:
        db_user = await crud.create_user(db=db, user=user)
        return schemas.UserResponse(
            id=db_user.id,
            email=db_user.email,
            success=True
        )
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/logout", response_model=schemas.UserResponse)
async def logout(user: schemas.UserCreate, db: Session = Depends(get_db)):
    logger.info(f"Logout attempt for email: {user.email}")
    try:
        clear_conversation_memory()
        return schemas.UserResponse(
            id=user.id,
            email=user.email,
            success=True
        )
    except Exception as e:
        logger.error(f"Error logging out: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/users/me", response_model=schemas.UserResponse)
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    return schemas.UserResponse(
        id=current_user.id,
        email=current_user.email,
        success=True
    )

@app.post("/api/conversations", response_model=schemas.ConversationResponse)
async def create_conversation(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        db_conversation = await crud.create_conversation(
            db, 
            current_user.id, 
            f"新しいチャット {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        return db_conversation
    except Exception as e:
        logger.error(f"Error creating conversation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.get("/api/users/{user_id}/conversations", response_model=schemas.ConversationListResponse)
async def get_user_conversations(
    user_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this resource"
        )
    try:
        conversations = await crud.get_user_conversations(db=db, user_id=user_id)
        return schemas.ConversationListResponse(
            conversations=conversations,
            success=True
        )
    except Exception as e:
        logger.error(f"Error getting conversations: {str(e)}")
        return schemas.ConversationListResponse(
            conversations=[],
            success=False,
            detail=str(e)
        )

@app.post("/api/chat", response_model=schemas.ChatResponse)
async def chat(
    request: schemas.ChatRequest, 
    current_user: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    req_data = request.dict()
    req_data['owner_id'] = current_user.id
    try:
        response_text = gemini_chat(req_data, db)
        return schemas.ChatResponse(response=response_text, success=True)
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/conversations/{conversation_id}/messages", response_model=schemas.MessagesResponse)
async def get_conversation_messages(
    conversation_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    try:
        conversation = await crud.get_conversation(db, conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found"
            )
        
        messages = await crud.get_conversation_messages(
            db=db,
            conversation_id=conversation_id,
            skip=skip,
            limit=limit
        )
        
        if messages is None:
            messages = []
            
        return schemas.MessagesResponse(messages=messages)
        
    except Exception as e:
        logger.error(f"Error getting conversation messages: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving messages: {str(e)}"
        )

@app.post("/api/upload-document", response_model=schemas.DocumentResponse)
@limiter.limit("5/minute") 
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    file_size = 0
    content = b""
    
    while chunk := await file.read(8192):
        content += chunk
        file_size += len(chunk)
        if file_size > FILE_SIZE_LIMIT:
            raise HTTPException(
                status_code=413,
                detail="ファイルサイズが大きすぎます。2MB以下のファイルを選択してください。"
            )
    
    try:
        content_str = content.decode('utf-8')
        doc_create = schemas.DocumentCreate(
            filename=file.filename,
            content=content_str
        )
        document = create_document(db, doc_create, current_user.id)
        return document
    except Exception as e:
        logger.error(f"ドキュメントのアップロードエラー: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@app.post("/upload-document", response_model=DocumentResponse)
async def upload_document(
    owner_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    content_bytes = await file.read()
    content = content_bytes.decode("utf-8")
    doc_data = DocumentCreate(filename=file.filename, content=content)
    db_doc = create_document(db, doc_data, owner_id)
    return db_doc

@app.delete("/api/conversations/{conversation_id}", response_model=schemas.DeleteResponse)
@limiter.limit("10/minute") 
async def delete_conversation(
    request: Request,
    conversation_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        conversation = await crud.get_conversation(db, conversation_id)
        if not conversation or conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=404,
                detail="会話が見つかりませんでした"
            )
        
        success = await crud.delete_conversation(db, conversation_id)
        if success:
            return schemas.DeleteResponse(
                success=True,
                message="会話が正常に削除されました"
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="会話の削除中にエラーが発生しました"
            )
    except Exception as e:
        logger.error(f"会話削除エラー: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.get("/health", tags=["Health"])
@limiter.limit("60/minute") 
async def health_check(request: Request, db: Session = Depends(get_db)):
    try:
        db.execute("SELECT 1")
        return {
            "status": "健康",
            "database": "接続済み",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"ヘルスチェックエラー: {str(e)}")
        return {
            "status": "不健康",
            "database": "接続エラー",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.middleware("http")
async def session_middleware(request: Request, call_next):
    exclude_paths = ["/api/login", "/api/signup", "/", "/static", "/api/conversations", "/api/users"]
    
    if not any(request.url.path.startswith(path) for path in exclude_paths):
        try:
            auth_header = request.headers.get("Authorization")
            if (auth_header and auth_header.startswith("Bearer ")):
                return await call_next(request)
                
            if "user_id" not in request.session:
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Session expired"}
                )
        except Exception as e:
            logger.error(f"Session middleware error: {str(e)}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Internal server error"}
            )
    
    response = await call_next(request)
    return response

@app.get("/api/documents/latest", response_model=schemas.DocumentResponse)
async def get_latest_document(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        document = get_document_by_user(db, current_user.id)
        if not document:
            raise HTTPException(
                status_code=404,
                detail="No document found for this user"
            )
        return document
    except Exception as e:
        logger.error(f"Error getting latest document: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)