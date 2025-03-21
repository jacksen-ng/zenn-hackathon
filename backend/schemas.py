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
    filename: str
    content: str

class DocumentCreate(DocumentBase):
    pass

class DocumentResponse(BaseModel):
    id: int
    filename: str
    content: str
    owner_id: int
    created_at: datetime
    success: bool

    class Config:
        from_attributes = True

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
    conversation_id: int
    text: str
    use_rag: bool = False
    # 允许接收来自前端的 user_id 字段，可为空
    user_id: Optional[int] = None
    document_path: Optional[str] = None
    document_id: Optional[int] = None
    # 用于后端传入当前用户ID
    owner_id: Optional[int] = None

    class Config:
        extra = "allow"

class ChatResponse(BaseModel):
    response: str
    success: bool
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
    user_id: int 
    conversation_id: int
    question: str
    response: str
    
    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "conversation_id": 1,
                "question": "Hello",
                "response": "Hi there!"
            }
        }

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