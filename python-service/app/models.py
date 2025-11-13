from typing import Optional
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    userId: str = Field(..., description="UUID of the user")
    sessionId: Optional[str] = Field(None, description="UUID of the chat session")
    message: str

class ChatResponse(BaseModel):
    reply: str
    sessionId: str
