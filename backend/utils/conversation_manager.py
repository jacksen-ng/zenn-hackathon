from langchain.memory import ConversationBufferMemory
from sqlalchemy.orm import Session
import crud
from typing import Optional, Dict, Tuple
from datetime import datetime

class ConversationManager:
    def __init__(self):
        self._memories: Dict[str, Tuple[ConversationBufferMemory, datetime]] = {}
        
    def _get_memory_key(self, user_id: int, conversation_id: int) -> str:
        return f"user_{user_id}_conv_{conversation_id}"
        
    async def get_or_create_memory(
        self,
        db: Session,
        user_id: int,
        conversation_id: int,
        max_age_minutes: int = 30
    ) -> ConversationBufferMemory:
        memory_key = self._get_memory_key(user_id, conversation_id)
        
        # Check if memory exists and is not expired
        if memory_key in self._memories:
            memory, created_at = self._memories[memory_key]
            age_minutes = (datetime.utcnow() - created_at).total_seconds() / 60
            
            if age_minutes < max_age_minutes:
                return memory
                
        # Create new memory and populate with conversation history
        memory = ConversationBufferMemory(return_messages=True)
        
        # Load conversation history from database
        messages = await crud.get_conversation_messages(
            db=db,
            conversation_id=conversation_id
        )
        
        # Populate memory with historical messages
        for msg in messages:
            memory.save_context(
                {"input": msg.question},
                {"output": msg.response}
            )
            
        # Store memory with timestamp
        self._memories[memory_key] = (memory, datetime.utcnow())
        return memory
        
    def clear_memory(self, user_id: int, conversation_id: int):
        memory_key = self._get_memory_key(user_id, conversation_id)
        if memory_key in self._memories:
            del self._memories[memory_key]

# Global instance
conversation_manager = ConversationManager()