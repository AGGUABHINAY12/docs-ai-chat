// API Configuration
const API_BASE_URL = 'http://localhost:8000/api';
let sessionId = localStorage.getItem('sessionId') || generateSessionId();
let currentMode = 'topic';
let currentDocument = null;
let currentQuiz = null;
let awaitingQuizAnswer = false;
let currentQuestionIndex = 0;

// DOM Elements
const messagesContainer = document.getElementById('messages-container');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const fileUpload = document.getElementById('file-upload');
const fileInfo = document.getElementById('file-info');
const modeTitle = document.getElementById('mode-title');
const quizControls = document.getElementById('quiz-controls');
const startQuizBtn = document.getElementById('start-quiz-btn');
const endQuizBtn = document.getElementById('end-quiz-btn');
const clearHistoryBtn = document.getElementById('clear-history');
const historyList = document.getElementById('history-list');

// Initialize
function init() {
    loadHistory();
    setupEventListeners();
    
    // Save session ID
    localStorage.setItem('sessionId', sessionId);
}

function generateSessionId() {
    return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
}

function setupEventListeners() {
    sendBtn.addEventListener('click', sendMessage);
    userInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    fileUpload.addEventListener('change', handleFileUpload);
    
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.addEventListener('click', () => switchMode(btn.dataset.mode));
    });
    
    startQuizBtn.addEventListener('click', startQuiz);
    endQuizBtn.addEventListener('click', endQuiz);
    clearHistoryBtn.addEventListener('click', clearHistory);
}

function switchMode(mode) {
    currentMode = mode;
    
    // Update UI
    document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === mode);
    });
    
    if (mode === 'quiz') {
        modeTitle.textContent = '🎯 Quiz Mode';
        quizControls.style.display = 'flex';
        addMessage('ai', '🎯 Quiz Mode activated! Upload a document first, then click "Start Quiz" to generate questions based on your material.');
    } else {
        modeTitle.textContent = '📖 Topic Study Mode';
        quizControls.style.display = 'none';
        currentQuiz = null;
        awaitingQuizAnswer = false;
        addMessage('ai', '📚 Topic Mode activated! Ask me questions about your document or request explanations.');
    }
}

async function handleFileUpload(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    fileInfo.innerHTML = '<i class="fas fa-spinner fa-pulse"></i> Uploading...';
    
    try {
        const response = await fetch(`${API_BASE_URL}/documents/upload`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            currentDocument = {
                id: data.document_id,
                name: data.file_name,
                content: data.content_preview
            };
            
            fileInfo.innerHTML = `<i class="fas fa-check-circle"></i> ${data.file_name}`;
            addMessage('ai', `✅ Document "${data.file_name}" uploaded successfully! I've analyzed the content. You can now ask questions or start a quiz.`);
        } else {
            throw new Error('Upload failed');
        }
    } catch (error) {
        console.error('Upload error:', error);
        fileInfo.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Upload failed';
        addMessage('ai', '❌ Failed to upload document. Please try again.');
    }
}

async function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;
    
    // Add user message to chat
    addMessage('user', message);
    userInput.value = '';
    
    // Handle quiz answers
    if (currentMode === 'quiz' && awaitingQuizAnswer && currentQuiz) {
        await handleQuizAnswer(message);
        return;
    }
    
    // Show typing indicator
    showTypingIndicator();
    
    try {
        const response = await fetch(`${API_BASE_URL}/chat/send`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                mode: currentMode,
                document_content: currentDocument?.content || '',
                file_name: currentDocument?.name || '',
                session_id: sessionId
            })
        });
        
        const data = await response.json();
        removeTypingIndicator();
        addMessage('ai', data.response);
        
        // Save to history
        saveToHistory(message, data.response);
        
    } catch (error) {
        console.error('Send message error:', error);
        removeTypingIndicator();
        addMessage('ai', 'Sorry, I encountered an error. Please try again.');
    }
}

async function startQuiz() {
    if (!currentDocument) {
        addMessage('ai', '📂 Please upload a document first before starting a quiz.');
        return;
    }
    
    addMessage('ai', '📝 Generating quiz questions from your document...');
    showTypingIndicator();
    
    try {
        const response = await fetch(`${API_BASE_URL}/chat/quiz/generate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                document_content: currentDocument.content,
                file_name: currentDocument.name,
                num_questions: 5
            })
        });
        
        const data = await response.json();
        removeTypingIndicator();
        
        if (data.success && data.questions) {
            currentQuiz = {
                questions: data.questions,
                currentIndex: 0,
                score: 0,
                answers: []
            };
            
            currentQuestionIndex = 0;
            awaitingQuizAnswer = true;
            displayNextQuestion();
        } else {
            addMessage('ai', 'Failed to generate quiz. Please make sure your document has enough content.');
        }
    } catch (error) {
        console.error('Quiz generation error:', error);
        removeTypingIndicator();
        addMessage('ai', 'Error generating quiz. Please try again.');
    }
}

function displayNextQuestion() {
    if (!currentQuiz || currentQuiz.currentIndex >= currentQuiz.questions.length) {
        endQuiz();
        return;
    }
    
    const question = currentQuiz.questions[currentQuiz.currentIndex];
    addMessage('ai', `**Question ${currentQuiz.currentIndex + 1} of ${currentQuiz.questions.length}**\n\n${question.question}\n\n📝 Type your answer below:`, true);
}

async function handleQuizAnswer(answer) {
    const question = currentQuiz.questions[currentQuestionIndex];
    
    showTypingIndicator();
    
    try {
        const response = await fetch(`${API_BASE_URL}/chat/quiz/answer`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                question_id: question.id,
                answer: answer,
                correct_answer: question.answer
            })
        });
        
        const data = await response.json();
        removeTypingIndicator();
        
        if (data.correct) {
            currentQuiz.score++;
            addMessage('ai', `✅ ${data.feedback}`);
        } else {
            addMessage('ai', `❌ ${data.feedback}`);
        }
        
        currentQuiz.answers.push({
            question: question.question,
            userAnswer: answer,
            correct: data.correct
        });
        
        currentQuiz.currentIndex++;
        currentQuestionIndex++;
        
        if (currentQuiz.currentIndex < currentQuiz.questions.length) {
            setTimeout(() => displayNextQuestion(), 1500);
        } else {
            setTimeout(() => showQuizResults(), 2000);
        }
        
    } catch (error) {
        console.error('Answer check error:', error);
        removeTypingIndicator();
        addMessage('ai', 'Error checking answer. Please try again.');
    }
}

function showQuizResults() {
    const total = currentQuiz.questions.length;
    const score = currentQuiz.score;
    const percentage = Math.round((score / total) * 100);
    
    let feedback = '';
    if (percentage >= 80) feedback = 'Excellent! 🎉 You mastered this material!';
    else if (percentage >= 60) feedback = 'Good job! 📚 Review the ones you missed.';
    else feedback = 'Keep studying! 💪 Try reviewing the document and take the quiz again.';
    
    addMessage('ai', `**📊 Quiz Complete!**\n\nScore: ${score}/${total} (${percentage}%)\n\n${feedback}\n\nType "Start Quiz" to try again or switch back to Topic mode for more study.`);
    
    currentQuiz = null;
    awaitingQuizAnswer = false;
}

function endQuiz() {
    currentQuiz = null;
    awaitingQuizAnswer = false;
    currentQuestionIndex = 0;
    addMessage('ai', 'Quiz ended. You can start a new quiz anytime by clicking "Start Quiz".');
}

function addMessage(role, content, isQuizQuestion = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    const icon = document.createElement('i');
    icon.className = role === 'user' ? 'fas fa-user' : 'fas fa-robot';
    
    const text = document.createElement('p');
    text.innerHTML = content.replace(/\n/g, '<br>');
    
    contentDiv.appendChild(icon);
    contentDiv.appendChild(text);
    messageDiv.appendChild(contentDiv);
    
    messagesContainer.appendChild(messageDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function showTypingIndicator() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message ai';
    typingDiv.id = 'typing-indicator';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    const indicator = document.createElement('div');
    indicator.className = 'typing-indicator';
    indicator.innerHTML = '<span></span><span></span><span></span>';
    
    contentDiv.appendChild(indicator);
    typingDiv.appendChild(contentDiv);
    messagesContainer.appendChild(typingDiv);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

function removeTypingIndicator() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) indicator.remove();
}

function saveToHistory(userMessage, aiResponse) {
    let history = JSON.parse(localStorage.getItem('chatHistory') || '[]');
    history.unshift({
        user: userMessage,
        ai: aiResponse,
        timestamp: new Date().toISOString(),
        mode: currentMode
    });
    
    // Keep only last 50 messages
    if (history.length > 50) history = history.slice(0, 50);
    
    localStorage.setItem('chatHistory', JSON.stringify(history));
    loadHistory();
}

function loadHistory() {
    const history = JSON.parse(localStorage.getItem('chatHistory') || '[]');
    
    if (history.length === 0) {
        historyList.innerHTML = '<div class="history-empty"><i class="fas fa-comments"></i><p>No history yet</p></div>';
        return;
    }
    
    historyList.innerHTML = history.map(item => `
        <div class="history-item" onclick="restoreConversation('${escapeHtml(item.user)}')">
            <i class="fas fa-comment"></i>
            <span>${escapeHtml(item.user.substring(0, 50))}${item.user.length > 50 ? '...' : ''}</span>
            <small>${new Date(item.timestamp).toLocaleTimeString()}</small>
        </div>
    `).join('');
}

function clearHistory() {
    if (confirm('Clear all conversation history?')) {
        localStorage.removeItem('chatHistory');
        loadHistory();
        addMessage('ai', 'History cleared! Ready for a fresh study session.');
    }
}

function restoreConversation(message) {
    userInput.value = message;
    userInput.focus();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Initialize app
init();