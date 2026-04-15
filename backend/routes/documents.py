from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import os
import shutil
import uuid
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.pdf_parser import PDFParser

router = APIRouter()

# Store documents
documents = {}

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """Upload and process a document"""
    try:
        doc_id = str(uuid.uuid4())
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        # Create uploads directory
        os.makedirs("uploads", exist_ok=True)
        
        # Save file
        file_path = f"uploads/{doc_id}{file_extension}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Extract text based on file type
        content = ""
        if file_extension == '.pdf':
            content = await PDFParser.extract_text(file_path)
        elif file_extension == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        else:
            content = f"[{file_extension.upper()} file: {file.filename}]"
        
        # Store document info
        documents[doc_id] = {
            "id": doc_id,
            "name": file.filename,
            "path": file_path,
            "content": content[:10000],  # Limit length
            "type": file_extension,
            "size": os.path.getsize(file_path)
        }
        
        return JSONResponse(content={
            "success": True,
            "document_id": doc_id,
            "file_name": file.filename,
            "content_preview": content[:500],
            "content_length": len(content)
        })
    
    except Exception as e:
        print(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.get("/{document_id}")
async def get_document(document_id: str):
    """Get document by ID"""
    if document_id in documents:
        return documents[document_id]
    raise HTTPException(status_code=404, detail="Document not found")

@router.get("/{document_id}/content")
async def get_document_content(document_id: str):
    """Get document content"""
    if document_id in documents:
        return {
            "content": documents[document_id]["content"],
            "file_name": documents[document_id]["name"]
        }
    raise HTTPException(status_code=404, detail="Document not found")

@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """Delete document"""
    if document_id in documents:
        if os.path.exists(documents[document_id]["path"]):
            os.remove(documents[document_id]["path"])
        del documents[document_id]
        return {"success": True, "message": "Document deleted"}
    raise HTTPException(status_code=404, detail="Document not found")