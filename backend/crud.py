from sqlalchemy.orm import Session
from sqlalchemy import desc
import models, schemas
from typing import Optional, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

async def create_user(db: Session, user: schemas.UserCreate):
    try:
        db_user = models.User(
            email=user.email,
            password=user.password  
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating user: {str(e)}")
        raise

async def get_user(db: Session, user_id: int):
    try:
        return db.query(models.User).filter(models.User.id == user_id).first()
    except Exception as e:
        logger.error(f"Error getting user: {str(e)}")
        raise

async def verify_user(db: Session, email: str, password: str):
    try:
        logger.info(f"Attempting to verify user with email: {email}")
        user = db.query(models.User).filter(models.User.email == email).first()
        if user and user.password == password:  
            return user
        return None
    except Exception as e:
        logger.error(f"Error verifying user: {str(e)}")
        raise

async def create_document(db: Session, document: schemas.DocumentCreate):
    try:
        now = datetime()
        db_document = models.Document(
            content=document.content,
            file_name=document.file_name,
            created_at=now,
            updated_at=now
        )
        db.add(db_document)
        db.commit()
        db.refresh(db_document)
        return db_document
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating document: {str(e)}")
        raise

async def get_all_documents(db: Session):
    try:
        return db.query(models.Document).all()
    except Exception as e:
        logger.error(f"Error getting all documents: {str(e)}")
        raise

async def get_document(db: Session, document_id: int):
    try:
        return db.query(models.Document).filter(models.Document.id == document_id).first()
    except Exception as e:
        logger.error(f"Error getting document: {str(e)}")
        raise

async def delete_document(db: Session, document_id: int):
    try:
        document = await get_document(db, document_id)
        if document:
            db.delete(document)
            db.commit()
        return document
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting document: {str(e)}")
        raise

async def create_conversation(db: Session, user_id: int, title: str = "New Conversation"):
    try:
        now = datetime.utcnow()
        db_conversation = models.Conversation(
            user_id=user_id,
            title=title,
            created_at=now,
            updated_at=now
        )
        db.add(db_conversation)
        db.commit()
        db.refresh(db_conversation)
        return db_conversation
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating conversation: {str(e)}")
        raise

async def get_user_conversations(db: Session, user_id: int) -> List[models.Conversation]:
    try:
        conversations = db.query(models.Conversation)\
                        .filter(models.Conversation.user_id == user_id)\
                        .order_by(desc(models.Conversation.updated_at))\
                        .all()
        return conversations if conversations else []
    except Exception as e:
        logger.error(f"Error getting user conversations: {str(e)}")
        raise

async def get_conversation(db: Session, conversation_id: int):
    try:
        return db.query(models.Conversation)\
                    .filter(models.Conversation.id == conversation_id)\
                    .first()
    except Exception as e:
        logger.error(f"Error getting conversation: {str(e)}")
        raise

async def delete_conversation(db: Session, conversation_id: int):
    try:
        conversation = await get_conversation(db, conversation_id)
        if conversation:
            db.delete(conversation)
            db.commit()
            return True
        return False
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting conversation: {str(e)}")
        raise

# Chat operations
async def create_chat_history(db: Session, chat: schemas.ChatCreate):
    try:
        now = datetime.utcnow()
        
        if chat.conversation_id:
            conversation = await get_conversation(db, chat.conversation_id)
            if not conversation:
                raise ValueError(f"Conversation with id {chat.conversation_id} not found")
        
        elif chat.user_id:
            conversation = await create_conversation(db, chat.user_id)
            chat.conversation_id = conversation.id
        else:
            raise ValueError("Either conversation_id or user_id must be provided")
        
        db_chat = models.Chat(
            conversation_id=chat.conversation_id,
            user_id=chat.user_id,
            question=chat.question,
            response=chat.response,
            created_at=now
        )
        
        db.add(db_chat)
        
        conversation = await get_conversation(db, chat.conversation_id)
        if conversation:
            conversation.updated_at = now
        
        db.commit()
        db.refresh(db_chat)
        return db_chat
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating chat history: {str(e)}")
        raise

async def get_conversation_messages(
    db: Session,
    conversation_id: int,
    skip: int = 0,
    limit: int = 100
) -> List[models.Chat]:
    try:
        messages = db.query(models.Chat)\
                    .filter(models.Chat.conversation_id == conversation_id)\
                    .order_by(models.Chat.created_at)\
                    .offset(skip)\
                    .limit(limit)\
                    .all()
        return messages if messages else []
    except Exception as e:
        logger.error(f"Error getting conversation messages: {str(e)}")
        raise

async def get_user_chat_history(
    db: Session,
    user_id: int,
    skip: int = 0,
    limit: int = 100
) -> List[models.Chat]:
    try:
        messages = db.query(models.Chat)\
                    .filter(models.Chat.user_id == user_id)\
                    .order_by(desc(models.Chat.created_at))\
                    .offset(skip)\
                    .limit(limit)\
                    .all()
        return messages if messages else []
    except Exception as e:
        logger.error(f"Error getting user chat history: {str(e)}")
        raise
        