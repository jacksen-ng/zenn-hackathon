import google.generativeai as genai
import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from schemas import ChatResponse, ChatRequest
from typing import AsyncGenerator
import json
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain.callbacks.streaming_stdout import StreamingStdOutCallbackHandler

load_dotenv()

# 環境変数からAPIキーを取得
GOOGLE_API_KEY = os.getenv("API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("API_KEY is not set in the environment variables")

# 会話メモリの辞書
conversation_memories = {}

# 会話IDに基づいてメモリを取得または作成
def get_or_create_memory(conversation_id: int):
    if conversation_id not in conversation_memories:
        conversation_memories[conversation_id] = ConversationBufferMemory()
    return conversation_memories[conversation_id]

# Gemini APIを使用してチャットを生成
async def gemini_chat(request: ChatRequest, db: Session) -> ChatResponse:
    try:
        # 会話IDに基づいてメモリを取得または作成
        memory = get_or_create_memory(request.conversation_id)
        
        # Geminiモデルのインスタンスを作成
        llm = ChatGoogleGenerativeAI(
            model="gemini-pro",
            temperature=0.7,
            google_api_key=GOOGLE_API_KEY,
            convert_system_message_to_human=True
        )
        
        # 会話チェーンを作成
        conversation = ConversationChain(
            llm=llm,
            memory=memory,
            verbose=True
        )
        
        # チャットを生成
        response = await conversation.arun(request.text)
        
        # 空の応答が返された場合、エラーを発生
        if not response:
            raise ValueError("Empty response from Gemini")
        
        # 応答を返す
        return ChatResponse(
            response=response,
            success=True,
            detail=None,
            created_at=None
        )
        
    except Exception as e:
        return ChatResponse(
            response="",
            success=False,
            detail=str(e),
            created_at=None
        )

#　これはチャットGPTみたいな回答仕方。ただ、フロントの方まだ完成していない
async def gemini_chat_stream(request: ChatRequest, db: Session) -> AsyncGenerator[str, None]:
    try:
        # 会話IDに基づいてメモリを取得または作成
        memory = get_or_create_memory(request.conversation_id)
        
        # Geminiモデルのインスタンスを作成
        llm = ChatGoogleGenerativeAI(
            model="gemini-pro",
            temperature=0.7,
            google_api_key=GOOGLE_API_KEY,
            streaming=True,
            callbacks=[StreamingStdOutCallbackHandler()],
            convert_system_message_to_human=True
        )
        
        # 会話チェーンを作成
        conversation = ConversationChain(
            llm=llm,
            memory=memory,
            verbose=True
        )
        
        response_stream = await conversation.arun(request.text)
            
        for chunk in response_stream:
            if chunk:
                yield f"data: {json.dumps({'content': chunk})}\n\n"
            
    except Exception as e:
        error_message = json.dumps({"error": str(e)})
        yield f"data: {error_message}\n\n"

def clear_conversation_memory(conversation_id: int):
    if conversation_id in conversation_memories:
        del conversation_memories[conversation_id]
        return True
    return False

def get_conversation_history(conversation_id: int):
    memory = get_or_create_memory(conversation_id)
    return memory.chat_memory.messages