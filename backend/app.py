from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
import uuid
import shutil
import re
from datetime import datetime, timedelta
from typing import Optional

# Try to import PDF library
try:
    from PyPDF2 import PdfReader
    PDF_OK = True
except:
    PDF_OK = False
    print("⚠️ PyPDF2 not installed. PDF support limited.")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage
documents = {}
sessions = {}
users = {
    "demo@smartprep.com": {"password": "demo123", "name": "Demo User"},
}
active_tokens = {}

# Helper: Extract sentences from text
def extract_sentences(text):
    # Split by periods, question marks, exclamation marks
    sentences = re.split(r'[.!?]+', text)
    # Clean up
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
    return sentences

# Helper: Find relevant sentences based on query
def find_relevant_sentences(query, document_content, max_sentences=3):
    if not document_content:
        return []
    
    query_words = set(query.lower().split())
    # Remove common stop words
    stop_words = {'what', 'is', 'are', 'the', 'a', 'an', 'of', 'to', 'in', 'for', 'on', 'with', 'by', 'at', 'from', 'up', 'down', 'and', 'or', 'so', 'but', 'if', 'then', 'else', 'when', 'where', 'which', 'while', 'this', 'that', 'these', 'those', 'it', 'they', 'we', 'you', 'he', 'she', 'me', 'him', 'her', 'us', 'them'}
    query_keywords = [w for w in query_words if w not in stop_words and len(w) > 2]
    
    sentences = extract_sentences(document_content)
    if not sentences:
        return []
    
    # Score each sentence by keyword matches
    scored = []
    for sent in sentences:
        sent_lower = sent.lower()
        score = sum(1 for kw in query_keywords if kw in sent_lower)
        # Also give partial credit for word overlaps
        if score > 0:
            scored.append((score, sent))
    
    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)
    
    # Return top matches
    return [sent for _, sent in scored[:max_sentences]]

@app.post("/api/auth/login")
async def login(request: dict):
    email = request.get("email", "").strip().lower()
    password = request.get("password", "")
    if email in users and users[email]["password"] == password:
        token = str(uuid.uuid4())
        expiry = datetime.now() + timedelta(days=7)
        active_tokens[token] = expiry
        return {"success": True, "token": token, "user": {"email": email, "name": users[email]["name"]}}
    return {"success": False, "error": "Invalid email or password"}

@app.post("/api/auth/register")
async def register(request: dict):
    email = request.get("email", "").strip().lower()
    password = request.get("password", "")
    name = request.get("name", "")
    if not email or not password:
        return {"success": False, "error": "Email and password required"}
    if email in users:
        return {"success": False, "error": "Email already exists"}
    users[email] = {"password": password, "name": name or email.split('@')[0]}
    token = str(uuid.uuid4())
    expiry = datetime.now() + timedelta(days=7)
    active_tokens[token] = expiry
    return {"success": True, "token": token, "user": {"email": email, "name": users[email]["name"]}}

@app.post("/api/auth/logout")
async def logout(request: dict):
    token = request.get("token", "")
    if token in active_tokens:
        del active_tokens[token]
    return {"success": True}

@app.get("/api/health")
async def health_check():
    return {"status": "OK"}

@app.post("/api/documents/upload")
async def upload_document(file: UploadFile = File(...)):
    try:
        doc_id = str(uuid.uuid4())
        file_ext = os.path.splitext(file.filename)[1].lower()
        os.makedirs("uploads", exist_ok=True)
        file_path = f"uploads/{doc_id}{file_ext}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        content = ""
        if file_ext == '.pdf' and PDF_OK:
            try:
                reader = PdfReader(file_path)
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        content += text + "\n"
            except Exception as e:
                content = f"Error reading PDF: {str(e)}"
        elif file_ext == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            content = f"[{file_ext} file uploaded: {file.filename}]"
        
        # Store full content (up to 15000 chars for performance)
        documents[doc_id] = {
            "id": doc_id,
            "name": file.filename,
            "content": content[:15000],
            "type": file_ext
        }
        
        return {
            "success": True,
            "document_id": doc_id,
            "file_name": file.filename,
            "content": content[:15000],  # Return full content to frontend
            "content_length": len(content)
        }
    except Exception as e:
        print(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/send")
async def send_message(request: dict):
    try:
        message = request.get("message", "")
        doc_content = request.get("document_content", "")
        doc_name = request.get("file_name", "")
        session_id = request.get("session_id", str(uuid.uuid4()))
        
        msg_lower = message.lower()
        has_doc = bool(doc_content and len(doc_content) > 100)
        
        # Greeting
        if any(word in msg_lower for word in ['hello', 'hi', 'hey', 'greetings']):
            response = "👋 Hello! I'm SmartPrep AI. Upload a PDF and ask me questions about it. I'll find relevant information from your document."
        
        elif not has_doc:
            response = "📚 Please upload a PDF document first. I can then answer questions, summarize, and explain concepts from your document."
        
        else:
            # Find relevant sentences from document content
            relevant_sents = find_relevant_sentences(message, doc_content, max_sentences=4)
            
            if relevant_sents:
                # Build response from relevant sentences
                answer = "\n\n".join([f"• {s}" for s in relevant_sents])
                response = f"📖 **Based on your document '{doc_name}':**\n\n{answer}\n\n💡 Is there anything specific you'd like me to clarify?"
            else:
                # Fallback: give a preview of the document and ask for more specific question
                preview = doc_content[:400]
                response = f"📄 I couldn't find a direct answer to your question in the document. Here's a preview of the content:\n\n{preview}...\n\nCould you rephrase your question or ask about a specific topic mentioned?"
        
        # Store in session
        if session_id not in sessions:
            sessions[session_id] = []
        sessions[session_id].append({"role": "user", "content": message})
        sessions[session_id].append({"role": "assistant", "content": response})
        
        return {
            "response": response,
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        print(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/history/{session_id}")
async def get_history(session_id: str):
    if session_id in sessions:
        return {"history": sessions[session_id], "session_id": session_id}
    return {"history": [], "session_id": session_id}

@app.delete("/api/chat/history/{session_id}")
async def clear_history(session_id: str):
    if session_id in sessions:
        sessions[session_id] = []
    return {"message": "History cleared"}

if __name__ == "__main__":
    print("\n" + "="*50)
    print("🚀 SmartPrep AI Server Starting...")
    print("📍 http://localhost:8000")
    print("="*50 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)