from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, BackgroundTasks, Request, status, Response
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


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建数据库表
Base.metadata.create_all(bind=engine)

# 创建 FastAPI 应用
app = FastAPI()

# 添加 Session 中间件（必须在其他中间件之前）
app.add_middleware(
    SessionMiddleware,
    secret_key=secrets.token_urlsafe(32),
    session_cookie="session",
    max_age=1800,  # 30分钟
    same_site="lax",
    https_only=False  # 开发环境设为 False
)

# 然后添加其他中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# 错误处理中间件
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

# 配置模板和静态文件
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# 主页路由
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# 用户相关端点
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
    user = await authenticate_user(form_data.username, form_data.password)
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
        
        # 创建访问令牌
        access_token = jwt_utils.create_access_token(data={"sub": user.email})
        
        # 检查用户是否有对话记录
        conversations = await crud.get_user_conversations(db, user.id)
        
        # 如果没有对话记录，创建新对话
        if not conversations:
            new_conversation = await crud.create_conversation(
                db=db,
                user_id=user.id,
                title=f"新しいチャット {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            conversation_id = new_conversation.id
        else:
            conversation_id = conversations[0].id
        
        # 在 session 中保存用户信息
        request.session["user_id"] = user.id
        request.session["email"] = user.email
        
        return schemas.UserResponse(
            id=user.id,
            email=user.email,
            success=True,
            token=access_token,
            conversation_id=conversation_id  # 添加会话ID到响应中
        )
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
        
# signup
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

# logout
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

# 需要认证的端点示例
@app.get("/api/users/me", response_model=schemas.UserResponse)
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    return schemas.UserResponse(
        id=current_user.id,
        email=current_user.email,
        success=True
    )

# 修改会话相关端点
@app.post("/api/conversations", response_model=schemas.ConversationResponse)
async def create_conversation(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # 创建新对话，使用默认标题
        db_conversation = await crud.create_conversation(
            db, 
            current_user.id, 
            f"新对话 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
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
    # 验证用户只能访问自己的会话
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

# 修改聊天相关端点
@app.post("/api/chat", response_model=schemas.ChatResponse)
async def chat(
    request: schemas.ChatRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        # 使用当前认证用户的 ID
        request.user_id = current_user.id
        
        logger.info(f"Received chat request: {request}")
        
        if not request.conversation_id or not request.user_id:
            raise HTTPException(
                status_code=400,
                detail="Missing conversation_id or user_id"
            )
        
        # 验证会话存在
        conversation = await crud.get_conversation(db, request.conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found"
            )
        
        # 调用 Gemini API 获取响应
        gemini_response = await gemini_chat(request, db)
        
        if not gemini_response.success:
            logger.error(f"Gemini API error: {gemini_response.detail}")
            return schemas.ChatResponse(
                response="",
                success=False,
                detail=gemini_response.detail or "Failed to get response from Gemini",
                created_at=None
            )
            
        # 保存聊天记录到数据库
        chat_create = schemas.ChatCreate(
            user_id=request.user_id,
            conversation_id=request.conversation_id,
            question=request.text,
            response=gemini_response.response
        )
        
        try:
            chat_message = await crud.create_chat_history(db=db, chat=chat_create)
            logger.info(f"Chat message saved with id: {chat_message.id}")
            
            return schemas.ChatResponse(
                response=gemini_response.response,
                success=True,
                detail=None,
                created_at=chat_message.created_at
            )
        except Exception as e:
            logger.error(f"Error saving chat message: {str(e)}")
            # 即使保存失败也返回响应
            return schemas.ChatResponse(
                response=gemini_response.response,
                success=True,
                detail=None,
                created_at=datetime.utcnow()
            )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return schemas.ChatResponse(
            response="",
            success=False,
            detail=str(e),
            created_at=None
        )

@app.get("/api/conversations/{conversation_id}/messages", response_model=schemas.MessagesResponse)
async def get_conversation_messages(
    conversation_id: int,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    try:
        # 验证会话存在
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


# 健康检查端点
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# 修改 session 验证中间件
@app.middleware("http")
async def session_middleware(request: Request, call_next):
    # 排除不需要验证的路径
    exclude_paths = ["/api/login", "/api/signup", "/", "/static", "/api/conversations", "/api/users"]
    
    if not any(request.url.path.startswith(path) for path in exclude_paths):
        try:
            # 检查 Authorization header
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                # 如果有 Bearer token，跳过 session 检查
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)