// Chatbot Widget JavaScript

class Chatbot {
    constructor() {
        this.isOpen = false;
        this.sessionId = this.getSessionId();
        this.isTyping = false;
        
        this.initElements();
        this.attachEventListeners();
        this.loadHistory();
    }
    
    initElements() {
        this.button = document.getElementById('chatbot-button');
        this.window = document.getElementById('chatbot-window');
        this.closeBtn = document.getElementById('chatbot-close');
        this.messagesContainer = document.getElementById('chatbot-messages');
        this.input = document.getElementById('chatbot-input');
        this.sendBtn = document.getElementById('chatbot-send');
        this.quickActions = document.querySelectorAll('.quick-action-btn');
    }
    
    attachEventListeners() {
        // Toggle chat window
        this.button.addEventListener('click', () => this.toggle());
        this.closeBtn.addEventListener('click', () => this.close());
        
        // Send message
        this.sendBtn.addEventListener('click', () => this.sendMessage());
        this.input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });
        
        // Quick actions
        this.quickActions.forEach(btn => {
            btn.addEventListener('click', () => {
                const message = btn.dataset.message;
                this.input.value = message;
                this.sendMessage();
            });
        });
    }
    
    getSessionId() {
        let sessionId = localStorage.getItem('chatbot_session_id');
        if (!sessionId) {
            sessionId = this.generateUUID();
            localStorage.setItem('chatbot_session_id', sessionId);
        }
        return sessionId;
    }
    
    generateUUID() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }
    
    toggle() {
        if (this.isOpen) {
            this.close();
        } else {
            this.open();
        }
    }
    
    open() {
        this.isOpen = true;
        this.window.classList.add('active');
        this.button.classList.add('active');
        this.input.focus();
        this.scrollToBottom();
    }
    
    close() {
        this.isOpen = false;
        this.window.classList.remove('active');
        this.button.classList.remove('active');
    }
    
    async loadHistory() {
        try {
            const response = await fetch(`/chatbot/api/chat/history/${this.sessionId}`);
            const data = await response.json();
            
            if (data.messages && data.messages.length > 0) {
                // Clear welcome message if exists
                const welcomeMsg = this.messagesContainer.querySelector('.welcome-message');
                if (welcomeMsg) {
                    welcomeMsg.remove();
                }
                
                // Display messages
                data.messages.forEach(msg => {
                    this.addMessage(msg.message, 'user', false);
                    this.addMessage(msg.response, 'bot', false);
                });
                
                this.scrollToBottom();
            }
        } catch (error) {
            console.error('Error loading chat history:', error);
        }
    }
    
    async sendMessage() {
        const message = this.input.value.trim();
        
        if (!message || this.isTyping) {
            return;
        }
        
        // Clear input
        this.input.value = '';
        
        // Remove welcome message if exists
        const welcomeMsg = this.messagesContainer.querySelector('.welcome-message');
        if (welcomeMsg) {
            welcomeMsg.remove();
        }
        
        // Add user message
        this.addMessage(message, 'user');
        
        // Show typing indicator
        this.showTyping();
        
        // Disable input
        this.isTyping = true;
        this.sendBtn.disabled = true;
        
        try {
            const response = await fetch('/chatbot/api/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: message,
                    session_id: this.sessionId
                })
            });
            
            const data = await response.json();
            
            if (data.error) {
                throw new Error(data.error);
            }
            
            // Hide typing indicator
            this.hideTyping();
            
            // Add bot response
            this.addMessage(data.response, 'bot');
            
        } catch (error) {
            console.error('Error sending message:', error);
            this.hideTyping();
            this.addMessage('Sorry, I encountered an error. Please try again.', 'bot');
        } finally {
            this.isTyping = false;
            this.sendBtn.disabled = false;
            this.input.focus();
        }
    }
    
    addMessage(text, sender, scroll = true) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${sender}`;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = sender === 'user' ? '👤' : '🤖';
        
        const content = document.createElement('div');
        content.className = 'message-content';
        
        // Convert markdown-like formatting to HTML
        const formattedText = this.formatMessage(text);
        content.innerHTML = formattedText;
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(content);
        
        this.messagesContainer.appendChild(messageDiv);
        
        if (scroll) {
            this.scrollToBottom();
        }
    }
    
    formatMessage(text) {
        // Simple formatting: convert **bold** to <strong>, *italic* to <em>
        let formatted = text
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>');
        
        return formatted;
    }
    
    showTyping() {
        const typingDiv = document.createElement('div');
        typingDiv.className = 'typing-indicator';
        typingDiv.id = 'typing-indicator';
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = '🤖';
        
        const content = document.createElement('div');
        content.className = 'message-content';
        
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('div');
            dot.className = 'typing-dot';
            content.appendChild(dot);
        }
        
        typingDiv.appendChild(avatar);
        typingDiv.appendChild(content);
        
        this.messagesContainer.appendChild(typingDiv);
        this.scrollToBottom();
    }
    
    hideTyping() {
        const typingIndicator = document.getElementById('typing-indicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }
    
    scrollToBottom() {
        setTimeout(() => {
            this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        }, 100);
    }
    
    clearSession() {
        if (confirm('Are you sure you want to clear the chat history?')) {
            fetch(`/chatbot/api/chat/session/${this.sessionId}`, {
                method: 'DELETE'
            })
            .then(() => {
                // Clear messages
                this.messagesContainer.innerHTML = `
                    <div class="welcome-message">
                        <div class="welcome-message-icon">🤖</div>
                        <h4>Hello! I'm your library assistant</h4>
                        <p>Ask me about books, check availability, or get recommendations!</p>
                    </div>
                `;
                
                // Generate new session ID
                this.sessionId = this.generateUUID();
                localStorage.setItem('chatbot_session_id', this.sessionId);
            })
            .catch(error => {
                console.error('Error clearing session:', error);
                alert('Failed to clear chat history');
            });
        }
    }
}

// Initialize chatbot when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.chatbot = new Chatbot();
});
