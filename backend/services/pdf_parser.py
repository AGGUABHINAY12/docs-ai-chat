import io
import os

try:
    from PyPDF2 import PdfReader
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    print("⚠️ PyPDF2 not installed. Install with: pip install PyPDF2")

class PDFParser:
    @staticmethod
    async def extract_text(file_path: str) -> str:
        """Extract text from PDF file"""
        if not PDF_AVAILABLE:
            return f"[PDF file: {os.path.basename(file_path)} - Install PyPDF2]"
        
        try:
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
            
            if text.strip():
                return text
            else:
                return f"[PDF file: {os.path.basename(file_path)} - No text found]"
        except Exception as e:
            print(f"PDF parsing error: {e}")
            return f"Error parsing PDF: {str(e)}"
    
    @staticmethod
    async def extract_text_from_bytes(file_bytes: bytes) -> str:
        """Extract text from PDF bytes"""
        if not PDF_AVAILABLE:
            return "[PDF content - PyPDF2 not installed]"
        
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            text = ""
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
            return text if text.strip() else "[No text extracted]"
        except Exception as e:
            print(f"PDF parsing error: {e}")
            return f"Error: {str(e)}"