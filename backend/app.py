import streamlit as st
import PyPDF2
import re
import uuid
from datetime import datetime
import os

# ========== PAGE CONFIGURATION ==========
st.set_page_config(
    page_title="DocuAIChat - AI Document Assistant",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ========== CUSTOM CSS FOR BETTER UI ==========
st.markdown("""
<style>
    /* Main container */
    .main {
        background: linear-gradient(135deg, #0f0f12 0%, #1a1a2e 100%);
    }
    
    /* Chat messages */
    .user-message {
        background: linear-gradient(135deg, #4f46e5, #7c3aed);
        color: white;
        padding: 12px 18px;
        border-radius: 20px;
        margin: 10px 0;
        max-width: 70%;
        float: right;
        clear: both;
    }
    
    .ai-message {
        background: rgba(30, 41, 59, 0.9);
        color: #e2e8f0;
        padding: 12px 18px;
        border-radius: 20px;
        margin: 10px 0;
        max-width: 70%;
        float: left;
        clear: both;
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background: rgba(15, 23, 42, 0.95);
    }
    
    /* Upload button */
    .upload-btn {
        background: linear-gradient(135deg, #4f46e5, #7c3aed);
        color: white;
        padding: 10px 20px;
        border-radius: 30px;
        text-align: center;
    }
    
    /* Title */
    h1 {
        background: linear-gradient(135deg, #818cf8, #c084fc);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
</style>
""", unsafe_allow_html=True)

# ========== SESSION STATE INITIALIZATION ==========
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'document_content' not in st.session_state:
    st.session_state.document_content = ""
if 'document_name' not in st.session_state:
    st.session_state.document_name = None
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'user_email' not in st.session_state:
    st.session_state.user_email = None

# ========== SIMPLE USER DATABASE (In-memory) ==========
users = {
    "demo@docuai.com": {"password": "demo123", "name": "Demo User"},
    "test@docuai.com": {"password": "test123", "name": "Test User"}
}

# ========== HELPER FUNCTIONS ==========
def extract_text_from_pdf(file):
    """Extract text from uploaded PDF"""
    try:
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"Error reading PDF: {str(e)}"

def clean_sentence(sentence):
    """Clean sentence from author names and extra spaces"""
    authors_to_remove = ['Chandrashekhar Goswami', 'C. Goswami', 'Goswami']
    for author in authors_to_remove:
        if sentence.endswith(author):
            sentence = sentence[:-len(author)].strip()
        if sentence.startswith(author):
            sentence = sentence[len(author):].strip()
    sentence = ' '.join(sentence.split())
    if sentence and not sentence.endswith(('.', '!', '?')):
        sentence += '.'
    return sentence

def get_best_answer(query, document_content):
    """Extract best answer from document based on query keywords"""
    if not document_content:
        return None
    
    query_words = set(query.lower().split())
    stop_words = {'what', 'is', 'are', 'the', 'a', 'an', 'of', 'to', 'in', 
                  'for', 'on', 'with', 'by', 'at', 'from', 'up', 'down', 'and', 
                  'or', 'so', 'but', 'if', 'then', 'else', 'when', 'where', 
                  'which', 'while', 'this', 'that', 'these', 'those', 'it', 
                  'they', 'we', 'you', 'he', 'she', 'me', 'him', 'her', 'us', 'them'}
    
    query_keywords = [w for w in query_words if w not in stop_words and len(w) > 2]
    
    # Split into sentences
    sentences = re.split(r'[.!?]+', document_content)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 30]
    
    if not sentences:
        return None
    
    # Score sentences by keyword matches
    scored = []
    for sent in sentences:
        sent_lower = sent.lower()
        score = sum(1 for kw in query_keywords if kw in sent_lower)
        if score > 0:
            scored.append((score, sent))
    
    if not scored:
        return clean_sentence(sentences[0])
    
    scored.sort(key=lambda x: x[0], reverse=True)
    return clean_sentence(scored[0][1])

def get_ai_response(message, doc_content, doc_name):
    """Generate AI response based on message and document"""
    msg_lower = message.lower()
    
    # Greeting
    if any(word in msg_lower for word in ['hello', 'hi', 'hey']):
        return "👋 Hello! I'm DocuAIChat. Upload a PDF document and ask me anything about it!"
    
    # No document uploaded
    if not doc_content:
        return "📚 Please upload a PDF document first. I can then answer questions, summarize, and explain concepts from your document."
    
    # Document-based questions
    answer = get_best_answer(message, doc_content)
    
    if answer:
        return answer
    else:
        preview = doc_content[:300].split('.')[0] + "."
        return f"I couldn't find a direct answer. Here's a related excerpt from '{doc_name}':\n\n{preview}"

# ========== LOGIN PAGE ==========
def login_page():
    st.markdown("""
    <div style="text-align: center; padding: 60px 20px;">
        <h1 style="font-size: 64px; margin-bottom: 20px;">📄 DocuAIChat</h1>
        <p style="font-size: 18px; color: #94a3b8;">AI-Powered Document Q&A Assistant</p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])
        
        with tab1:
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="demo@docuai.com")
                password = st.text_input("Password", type="password", placeholder="demo123")
                submitted = st.form_submit_button("Login", use_container_width=True)
                
                if submitted:
                    if email in users and users[email]["password"] == password:
                        st.session_state.authenticated = True
                        st.session_state.user_email = email
                        st.rerun()
                    else:
                        st.error("Invalid email or password. Try: demo@docuai.com / demo123")
        
        with tab2:
            with st.form("register_form"):
                name = st.text_input("Full Name", placeholder="John Doe")
                email = st.text_input("Email", placeholder="your@email.com")
                password = st.text_input("Password", type="password", placeholder="Create password")
                submitted = st.form_submit_button("Register", use_container_width=True)
                
                if submitted:
                    if email in users:
                        st.error("Email already exists!")
                    elif email and password:
                        users[email] = {"password": password, "name": name or email.split('@')[0]}
                        st.success("Registration successful! Please login.")
                    else:
                        st.error("Please fill all fields")

# ========== MAIN CHAT INTERFACE ==========
def main_chat():
    # Sidebar
    with st.sidebar:
        st.markdown("### 📄 DocuAIChat")
        st.markdown("---")
        
        # User info
        st.markdown(f"""
        <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 12px; margin-bottom: 20px;">
            <div style="display: flex; align-items: center; gap: 10px;">
                <div style="width: 40px; height: 40px; background: linear-gradient(135deg, #4f46e5, #7c3aed); border-radius: 50%; display: flex; align-items: center; justify-content: center;">
                    <span style="color: white;">👤</span>
                </div>
                <div>
                    <div style="font-weight: 600;">{users[st.session_state.user_email]['name']}</div>
                    <div style="font-size: 11px; color: #94a3b8;">{st.session_state.user_email}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Document Upload Section
        st.markdown("### 📁 Document")
        uploaded_file = st.file_uploader("Upload PDF", type=['pdf'], label_visibility="collapsed")
        
        if uploaded_file is not None:
            with st.spinner("Processing document..."):
                text = extract_text_from_pdf(uploaded_file)
                if text and len(text) > 100:
                    st.session_state.document_content = text[:15000]
                    st.session_state.document_name = uploaded_file.name
                    st.success(f"✅ {uploaded_file.name}")
                    st.info(f"📊 {len(text)} characters extracted")
                else:
                    st.error("Could not extract text. Try another PDF.")
        
        # Document status
        if st.session_state.document_name:
            st.markdown(f"""
            <div style="background: rgba(79, 70, 229, 0.15); padding: 10px; border-radius: 10px; margin-top: 10px;">
                <small>📄 Active: <strong>{st.session_state.document_name[:30]}</strong></small>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Clear chat button
        if st.button("🗑️ Clear Chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        
        # Logout button
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.messages = []
            st.session_state.document_content = ""
            st.session_state.document_name = None
            st.rerun()
        
        st.markdown("---")
        st.caption("💡 **Tips:**\n• Ask questions like 'What is X?'\n• 'Summarize this document'\n• 'Explain the key points'")
    
    # Main Chat Area
    st.markdown("""
    <div style="text-align: center; padding: 20px 0;">
        <h1>📄 DocuAIChat</h1>
        <p style="color: #94a3b8;">Ask questions about your document and get instant answers</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Chat history display
    chat_container = st.container()
    
    with chat_container:
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.markdown(f"""
                <div style="display: flex; justify-content: flex-end; margin: 10px 0;">
                    <div style="background: linear-gradient(135deg, #4f46e5, #7c3aed); color: white; padding: 12px 18px; border-radius: 20px; max-width: 70%;">
                        {msg["content"]}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="display: flex; justify-content: flex-start; margin: 10px 0;">
                    <div style="background: rgba(30, 41, 59, 0.9); color: #e2e8f0; padding: 12px 18px; border-radius: 20px; max-width: 70%; border: 1px solid rgba(255,255,255,0.05);">
                        <strong>🤖 DocuAI:</strong><br>{msg["content"]}
                    </div>
                </div>
                """, unsafe_allow_html=True)
    
    # Chat input
    st.markdown("---")
    
    col1, col2 = st.columns([5, 1])
    
    with col1:
        user_input = st.text_input("Ask a question about your document...", key="user_input", label_visibility="collapsed", placeholder="Type your question here...")
    
    with col2:
        send_button = st.button("Send 📤", use_container_width=True)
    
    if send_button and user_input:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Generate response
        with st.spinner("🤔 Thinking..."):
            response = get_ai_response(
                user_input,
                st.session_state.document_content,
                st.session_state.document_name
            )
        
        # Add AI response
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        # Rerun to update chat display
        st.rerun()

# ========== APP ROUTING ==========
def main():
    if not st.session_state.authenticated:
        login_page()
    else:
        main_chat()

if __name__ == "__main__":
    main()
