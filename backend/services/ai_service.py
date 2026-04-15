import random
from typing import List, Dict

class AIService:
    def __init__(self):
        print("🤖 AI Service initialized (Mock Mode)")
    
    async def generate_response(self, message: str, mode: str, document_content: str = "", file_name: str = "") -> str:
        """Generate AI response"""
        
        has_doc = bool(document_content and len(document_content) > 50)
        msg_lower = message.lower()
        
        # Greeting responses
        if any(word in msg_lower for word in ['hello', 'hi', 'hey', 'greetings']):
            return "👋 Hello! I'm SmartPrep AI. Upload a document (PDF, DOCX, PPT) and I'll help you study. Switch to Quiz mode to test your knowledge!"
        
        # Quiz mode
        if mode == "quiz":
            if any(word in msg_lower for word in ['start', 'generate', 'begin']):
                if has_doc:
                    return "📝 **Quiz Generated!**\n\n**Question 1:** Based on the document, what is the main topic or key concept discussed?\n\nType your answer below!"
                else:
                    return "📂 Please upload a document first (PDF, DOCX, or PPT) so I can generate relevant quiz questions for you."
            
            if any(word in msg_lower for word in ['end', 'stop']):
                return "Quiz ended. You can start a new quiz anytime by typing 'start quiz'."
            
            return "🎯 **Quiz Mode Active**\n\nCommands:\n• 'start quiz' - Generate questions from your document\n• 'end quiz' - Exit quiz mode"
        
        # Topic mode with document
        if has_doc:
            preview = document_content[:500]
            
            if 'summar' in msg_lower:
                return f"📌 **Summary of {file_name}**\n\n{preview}\n\nWould you like me to extract key points or create flashcards?"
            
            elif 'explain' in msg_lower or 'what is' in msg_lower:
                return f"🔍 **Explanation**\n\nBased on your document:\n\n{preview[:400]}\n\nWhat specific aspect would you like to explore further?"
            
            elif 'key point' in msg_lower or 'main idea' in msg_lower:
                return f"💡 **Key Points from {file_name}**\n\n• The document discusses important concepts\n• Examples illustrate the main arguments\n• Key takeaways are summarized\n\nWould you like me to elaborate on any point?"
            
            else:
                return f"📖 **From your document '{file_name}':**\n\n{preview[:600]}\n\n💡 Ask me to explain concepts, create a quiz, or summarize specific sections!"
        
        # Topic mode without document
        else:
            return "📚 **Topic Mode Active**\n\nUpload a PDF, DOCX, or PowerPoint file, and I'll help you:\n• Understand the content\n• Answer questions\n• Create study materials\n• Generate quizzes\n\nGo ahead and upload a document to get started!"
    
    async def generate_quiz_questions(self, document_content: str, file_name: str, num_questions: int = 5) -> List[Dict]:
        """Generate quiz questions from document"""
        
        questions = []
        
        if not document_content or len(document_content) < 50:
            # Fallback questions
            questions = [
                {
                    "id": 1,
                    "question": "What is the main topic of this document?",
                    "answer": "The document discusses key concepts related to the subject matter."
                },
                {
                    "id": 2,
                    "question": "What are the key points presented?",
                    "answer": "Important facts, examples, and conclusions that support the main topic."
                },
                {
                    "id": 3,
                    "question": "What is the most important takeaway?",
                    "answer": "Understanding the core concepts and being able to apply them."
                }
            ]
            return questions[:num_questions]
        
        # Generate from actual content
        sentences = [s.strip() for s in document_content.split('.') if len(s.strip()) > 30]
        
        for i in range(min(num_questions, len(sentences) if sentences else num_questions)):
            if i < len(sentences):
                sentence = sentences[i]
                q_text = sentence[:100] + "..." if len(sentence) > 100 else sentence
                questions.append({
                    "id": i + 1,
                    "question": f"Explain or describe: '{q_text}'",
                    "answer": sentence[:300]
                })
            else:
                questions.append({
                    "id": i + 1,
                    "question": f"What is an important concept from '{file_name}'?",
                    "answer": document_content[:300] if document_content else "The document contains important information."
                })
        
        # Add comprehensive question if needed
        if len(questions) < num_questions:
            questions.append({
                "id": num_questions,
                "question": f"What is the main purpose of '{file_name}'?",
                "answer": document_content[:300] if document_content else "The document aims to educate about the subject."
            })
        
        return questions[:num_questions]

# Create singleton instance
ai_service = AIService()