from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class UserCreate(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    success: bool = True
    detail: Optional[str] = None
    token: Optional[str] = None
    conversation_id: Optional[int] = None

    class Config:
        from_attributes = True

class DocumentBase(BaseModel):
    content: str
    file_name: str

class DocumentCreate(DocumentBase):
    pass

class Document(DocumentBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ConversationBase(BaseModel):
    title: str = "New Conversation"
    user_id: int

class ConversationCreate(ConversationBase):
    pass

class Conversation(ConversationBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ConversationResponse(BaseModel):
    id: int
    title: str
    user_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ConversationListResponse(BaseModel):
    conversations: List[Conversation]
    success: bool = True
    detail: Optional[str] = None

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ChatRequest(BaseModel):
    text: str
    conversation_id: Optional[int] = None
    user_id: Optional[int] = None

class ChatResponse(BaseModel):
    response: str
    success: bool = True
    detail: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }

class ChatMessageResponse(BaseModel):
    id: int
    question: str
    response: str
    created_at: datetime
    conversation_id: int
    user_id: int

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ConversationDetail(ConversationResponse):
    messages: List[ChatMessageResponse]

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class MessagesResponse(BaseModel):
    messages: List[ChatMessageResponse]

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ChatCreate(BaseModel):
    user_id: Optional[int] = None
    conversation_id: Optional[int] = None
    question: str
    response: str

class ChatHistory(ChatCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ErrorResponse(BaseModel):
    detail: str
    success: bool = False

class DeleteResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat() if v else None
        }
        
class ExpiredSignatureError(Exception):
    pass

class InvalidTokenError(Exception):
    pass