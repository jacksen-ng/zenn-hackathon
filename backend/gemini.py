import google.generativeai as genai
import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from schemas import ChatResponse, ChatRequest
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from datetime import datetime

load_dotenv()

GOOGLE_API_KEY = os.getenv("API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("API_KEY is not set in the environment variables")

conversation_memories = {}

def get_or_create_memory(conversation_id: int):
    if conversation_id not in conversation_memories:
        conversation_memories[conversation_id] = ConversationBufferMemory()
    return conversation_memories[conversation_id]

async def gemini_chat(request: ChatRequest, db: Session) -> ChatResponse:
    try:
        memory = get_or_create_memory(request.conversation_id)
        
        llm = ChatGoogleGenerativeAI(
            model="gemini-pro",
            temperature=0.7,
            google_api_key=GOOGLE_API_KEY
        )
        
        conversation = ConversationChain(
            llm=llm,
            memory=memory,
            verbose=False
        )
        
        # 获取响应
        response = await conversation.arun(request.text)
        
        if not response:
            raise ValueError("Empty response from Gemini")
        
        return ChatResponse(
            response=response,
            success=True,
            detail=None,
            created_at=datetime.utcnow()
        )
        
    except Exception as e:
        return ChatResponse(
            response="",
            success=False,
            detail=str(e),
            created_at=None
        )

def clear_conversation_memory(conversation_id: int):
    if conversation_id in conversation_memories:
        del conversation_memories[conversation_id]
        return True
    return False

def get_conversation_history(conversation_id: int):
    memory = get_or_create_memory(conversation_id)
    return memory.chat_memory.messages