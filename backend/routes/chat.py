from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
import uuid
from datetime import datetime
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.ai_service import ai_service

router = APIRouter()

# In-memory storage
sessions = {}

class ChatRequest(BaseModel):
    message: str
    mode: str = "topic"
    document_content: Optional[str] = ""
    file_name: Optional[str] = ""
    session_id: Optional[str] = None

class QuizRequest(BaseModel):
    document_content: str
    file_name: str
    num_questions: int = 5

class QuizAnswer(BaseModel):
    question_id: int
    answer: str
    correct_answer: str

@router.post("/send")
async def send_message(request: ChatRequest):
    """Send a message and get AI response"""
    try:
        session_id = request.session_id or str(uuid.uuid4())
        
        response = await ai_service.generate_response(
            message=request.message,
            mode=request.mode,
            document_content=request.document_content,
            file_name=request.file_name
        )
        
        # Store in session
        if session_id not in sessions:
            sessions[session_id] = []
        
        sessions[session_id].append({
            "role": "user",
            "content": request.message,
            "timestamp": datetime.now().isoformat()
        })
        sessions[session_id].append({
            "role": "assistant",
            "content": response,
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "response": response,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        print(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{session_id}")
async def get_history(session_id: str):
    """Get chat history"""
    if session_id in sessions:
        return {"history": sessions[session_id], "session_id": session_id}
    return {"history": [], "session_id": session_id}

@router.delete("/history/{session_id}")
async def clear_history(session_id: str):
    """Clear chat history"""
    if session_id in sessions:
        sessions[session_id] = []
    return {"message": "History cleared", "session_id": session_id}

@router.post("/quiz/generate")
async def generate_quiz(request: QuizRequest):
    """Generate quiz questions"""
    try:
        questions = await ai_service.generate_quiz_questions(
            document_content=request.document_content,
            file_name=request.file_name,
            num_questions=request.num_questions
        )
        return {"questions": questions, "success": True}
    except Exception as e:
        print(f"Quiz error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/quiz/answer")
async def check_answer(request: QuizAnswer):
    """Check quiz answer"""
    user_answer = request.answer.lower().strip()
    correct_answer = request.correct_answer.lower()
    
    # Simple answer checking
    is_correct = (
        len(user_answer) > 10 and 
        (user_answer in correct_answer or 
         any(word in correct_answer for word in user_answer.split()[:3]))
    )
    
    if is_correct:
        feedback = "✅ Correct! Great job!"
    else:
        preview = request.correct_answer[:150] + "..." if len(request.correct_answer) > 150 else request.correct_answer
        feedback = f"❌ Not quite. A good answer would include: {preview}"
    
    return {
        "correct": is_correct,
        "feedback": feedback,
        "expected": request.correct_answer[:200]
    }