import google.generativeai as genai
import os
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from schemas import ChatResponse, ChatRequest
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from datetime import datetime
from gemini_rag import Gemini_RAG
import tempfile
from crud import get_document_sync, get_document_by_id, get_document_by_user  # 导入新函数

load_dotenv()

GOOGLE_API_KEY = os.getenv("API_KEY")
MODEL = os.getenv("MODEL", "gemini-pro")
if not GOOGLE_API_KEY:
    raise ValueError("API_KEY is not set in the environment variables")

conversation_memories = {}
rag_instances = {} 

def get_or_create_memory(conversation_id: int):
    if conversation_id not in conversation_memories:
        conversation_memories[conversation_id] = ConversationBufferMemory()
    return conversation_memories[conversation_id]

def validate_document_path(path: str) -> bool:
    return path and os.path.exists(path) and os.path.isfile(path)

def get_or_create_rag(conversation_id: int, document_path: str = None):
    if conversation_id not in rag_instances:
        rag = Gemini_RAG()
        if document_path:
            if not validate_document_path(document_path):
                raise ValueError(f"Invalid or inaccessible document path: {document_path}")
            try:
                rag.save_text(document_path)
            except Exception as e:
                raise Exception(f"Failed to initialize RAG with document: {str(e)}")
        rag.run()
        rag_instances[conversation_id] = rag
    return rag_instances[conversation_id]

def reinitialize_rag(rag_instance, document_path: str, chunk_size: int = 100, chunk_overlap: int = 70):
    rag_instance.save_text(
        path=document_path,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    rag_instance.run()

def gemini_chat(request_data: dict, db: Session) -> str:
    try:
        print("Request data:", request_data)
        conversation_id = request_data.get('conversation_id')
        if not conversation_id:
            raise ValueError("Missing conversation_id")

        use_rag = request_data.get('use_rag', False)
        print(f"RAG mode enabled: {use_rag}")

        if use_rag:
            owner_id = request_data.get('owner_id')
            
            doc = get_document_by_user(db, owner_id)
            if not doc:
                raise ValueError("No document found for this user")
            
            try:
                rag = rag_instances.get(conversation_id)
                if not rag or not rag.is_initialized:
                    rag = Gemini_RAG()
                    rag.save_text(doc.content)
                    rag.run()
                    rag_instances[conversation_id] = rag
                elif rag.current_document != doc.id:
                    rag.save_text(doc.content)
                    rag.run()
                    rag.current_document = doc.id
            except Exception as e:
                print(f"Error initializing RAG: {str(e)}")
                raise

            response = str(rag.ask(
                prompt=request_data['text'],
                session_id=str(conversation_id)
            ))
            
            return response

        memory = get_or_create_memory(conversation_id)
        llm = ChatGoogleGenerativeAI(
            model=MODEL, 
            temperature=0.7,
            google_api_key=GOOGLE_API_KEY
        )
        conversation = ConversationChain(
            llm=llm,
            memory=memory,
            verbose=False
        )
        return conversation.run(request_data['text'])

    except Exception as e:
        print(f"Error in gemini_chat: {str(e)}")
        raise Exception(f"Chat error: {str(e)}")

def clear_conversation_memory(conversation_id: int):
    if conversation_id in conversation_memories:
        del conversation_memories[conversation_id]
    if conversation_id in rag_instances:
        del rag_instances[conversation_id]
    return True

def get_conversation_history(conversation_id: int):
    memory = get_or_create_memory(conversation_id)
    return memory.chat_memory.messages
