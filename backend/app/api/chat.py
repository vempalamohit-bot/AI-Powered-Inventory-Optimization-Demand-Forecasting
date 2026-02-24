"""Chat API for NLP-style inventory questions.

For now this uses a rule-based InventoryChatbot. Later you can
swap in a GenAI model while keeping this contract stable.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.chatbot import InventoryChatbot
from ..models.genai_client import GenAIClient


router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    answer: str
    intent: str


class ChatAnalysisRequest(BaseModel):
    # Full conversation as plain text or serialized messages
    transcript: str


class ChatAnalysisResponse(BaseModel):
    analysis: str


@router.post("/query", response_model=ChatResponse)
def chat_query(payload: ChatRequest, db: Session = Depends(get_db)):
    """Answer natural-language questions about inventory and sales.

    Example messages:
    - "How is my inventory overall?"
    - "What are my top selling products?"
    - "How many units of ICE_CREAM are in stock?"
    """
    try:
        bot = InventoryChatbot(db)
        result = bot.generate_answer(payload.message)
        base_answer = result["answer"]
        intent = result.get("intent", "unknown")

        # Optional GenAI rewrite for more natural, executive-style language
        genai = GenAIClient()
        final_answer = genai.rewrite_answer(payload.message, base_answer)

        return ChatResponse(answer=final_answer, intent=intent)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chatbot error: {e}")


@router.post("/analyze", response_model=ChatAnalysisResponse)
def analyze_chat(payload: ChatAnalysisRequest) -> ChatAnalysisResponse:
    """Run GenAI-powered analysis over a full chat transcript.

    This can be used to understand what a user asked over a session,
    key topics, risks, and follow-up actions.
    """
    try:
        genai = GenAIClient()
        analysis_text = genai.analyze_conversation(payload.transcript)
        return ChatAnalysisResponse(analysis=analysis_text)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat analysis error: {e}")
