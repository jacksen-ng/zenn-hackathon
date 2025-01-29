from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, BackgroundTasks, Request
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
from gemini import gemini_chat, gemini_chat_stream, clear_conversation_memory
from starlette.middleware.base import BaseHTTPMiddleware
from utils.conversation_manager import conversation_manager
from datetime import datetime
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

app = FastAPI()

templates = Jinja2Templates(directory="templates")

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# 試しに、フロントの方を作った
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/users", response_model=schemas.UserResponse)
async def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = await crud.create_user(db=db, user=user)
    return schemas.UserResponse(
        id=db_user.id,
        email=db_user.email,
        success=True
    )

@app.post("/api/login", response_model=schemas.UserResponse)
async def login(user_data: schemas.UserLogin, db: Session = Depends(get_db)):
    logger.info(f"Login attempt for email: {user_data.email}")
    try:
        user = await crud.verify_user(db=db, email=user_data.email, password=user_data.password)
        if not user:
            logger.warning(f"Login failed for email: {user_data.email}")
            raise HTTPException(
                status_code=401,
                detail="Incorrect email or password"
            )
        logger.info(f"Login successful for email: {user_data.email}")
        return schemas.UserResponse(
            id=user.id,
            email=user.email,
            success=True
        )
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.post("/api/conversations", response_model=schemas.ConversationResponse)
async def create_conversation(
    request: schemas.ConversationCreate,
    db: Session = Depends(get_db)
):
    try:
        conversation = await crud.create_conversation(
            db=db,
            user_id=request.user_id,
            title=request.title
        )
        return schemas.ConversationResponse(
            id=conversation.id,
            title=conversation.title,
            user_id=conversation.user_id,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at
        )
    except Exception as e:
        logger.error(f"Error creating conversation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.get("/api/users/{user_id}/conversations", response_model=schemas.ConversationListResponse)
async def get_user_conversations(user_id: int, db: Session = Depends(get_db)):
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
    db: Session = Depends(get_db)
):
    try:
        logger.info(f"Received chat request: {request}")
        
        if not request.conversation_id or not request.user_id:
            raise HTTPException(
                status_code=400,
                detail="Missing conversation_id or user_id"
            )
        

        conversation = await crud.get_conversation(db, request.conversation_id)
        if not conversation:
            raise HTTPException(
                status_code=404,
                detail="Conversation not found"
            )
        
        gemini_response = await gemini_chat(request, db)
        
        if not gemini_response.success:
            logger.error(f"Gemini API error: {gemini_response.detail}")
            return schemas.ChatResponse(
                response="",
                success=False,
                detail=gemini_response.detail or "Failed to get response from Gemini",
                created_at=None
            )
            
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

@app.post("/api/chat/stream")
async def chat_stream(
    request: schemas.ChatRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    async def save_chat_history():
        try:
            chat_record = schemas.ChatCreate(
                user_id=request.user_id,
                conversation_id=request.conversation_id,
                question=request.text,
                response="[Streaming Response]"
            )
            await crud.create_chat_history(db, chat_record)
        except Exception as e:
            logger.error(f"Error saving chat history: {str(e)}")

    background_tasks.add_task(save_chat_history)
    logger.info(f"Starting streaming response for request: {request.text[:100]}...")

    return StreamingResponse(
        gemini_chat_stream(request, db),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Transfer-Encoding": "chunked",
            "Access-Control-Allow-Origin": "*"
        }
    )

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)