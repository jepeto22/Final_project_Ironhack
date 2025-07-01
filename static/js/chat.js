class ChatBot {
    constructor() {
        this.isTyping = false;
        this.currentSessionId = null;
        this.currentMode = 'single';
        this.chatSessionActive = false;
        this.init();
    }

    init() {
        this.bindEvents();
        this.generateSessionId();
        this.showWelcomeMessage();
        this.createParticles();
        this.focusInput();
    }

    bindEvents() {
        const sendButton = document.getElementById('sendButton');
        const chatInput = document.getElementById('chatInput');
        const sampleQuestions = document.querySelectorAll('.sample-question');
        const clearButton = document.getElementById('clearButton');
        const modeSelect = document.getElementById('modeSelect');

        // Mode selection
        if (modeSelect) {
            modeSelect.addEventListener('change', (e) => {
                this.changeMode(e.target.value);
            });
        }

        // Send button click
        sendButton.addEventListener('click', () => this.sendMessage());

        // Enter key to send (Shift+Enter for new line)
        chatInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Auto-resize textarea
        chatInput.addEventListener('input', () => {
            this.adjustTextareaHeight();
        });

        // Sample questions
        sampleQuestions.forEach(button => {
            button.addEventListener('click', () => {
                const question = button.textContent.trim();
                this.sendMessageWithText(question);
            });
        });

        // Clear conversation
        if (clearButton) {
            clearButton.addEventListener('click', () => this.clearConversation());
        }
    }

    generateSessionId() {
        this.currentSessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    adjustTextareaHeight() {
        const textarea = document.getElementById('chatInput');
        textarea.style.height = 'auto';
        textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
    }

    focusInput() {
        setTimeout(() => {
            document.getElementById('chatInput').focus();
        }, 100);
    }

    showWelcomeMessage() {
        const messagesContainer = document.getElementById('chatMessages');
        const welcomeHtml = `
            <div class="welcome-message">
                <h2 class="welcome-title">🧬 Welcome to Kurzgesagt AI Assistant</h2>
                <p class="welcome-subtitle">
                    Ask me anything about science topics covered in Kurzgesagt videos! 
                    I can answer in multiple languages and remember our conversation context.
                </p>
                <div class="sample-questions">
                    <div class="sample-question">What are black holes?</div>
                    <div class="sample-question">How does the immune system work?</div>
                    <div class="sample-question">What would happen if the moon crashed into Earth?</div>
                    <div class="sample-question">Tell me about dinosaurs</div>
                </div>
            </div>
        `;
        messagesContainer.innerHTML = welcomeHtml;
        this.bindSampleQuestionEvents();
    }

    bindSampleQuestionEvents() {
        const sampleQuestions = document.querySelectorAll('.sample-question');
        sampleQuestions.forEach(button => {
            button.addEventListener('click', () => {
                const question = button.textContent.trim();
                this.sendMessageWithText(question);
            });
        });
    }

    createParticles() {
        const particlesContainer = document.getElementById('particles');
        const particleCount = 20;

        for (let i = 0; i < particleCount; i++) {
            const particle = document.createElement('div');
            particle.className = 'particle';
            particle.style.left = Math.random() * 100 + '%';
            particle.style.top = Math.random() * 100 + '%';
            particle.style.animationDelay = Math.random() * 8 + 's';
            particlesContainer.appendChild(particle);
        }
    }

    async sendMessage() {
        const input = document.getElementById('chatInput');
        const message = input.value.trim();
        
        if (!message || this.isTyping) return;

        this.sendMessageWithText(message);
        input.value = '';
        this.adjustTextareaHeight();
    }

    async sendMessageWithText(message) {
        if (this.isTyping) return;

        // Clear welcome message if it exists
        this.clearWelcomeMessage();

        // Add user message
        this.addMessage(message, 'user');

        // Show typing indicator
        this.showTypingIndicator();

        try {
            // Check if we're in chat mode and handle accordingly
            if (this.currentMode === 'chat' && this.chatSessionActive) {
                this.hideTypingIndicator();
                await this.sendChatMessage(message);
            } else {
                // Use single message mode
                const response = await this.callAPI(message);
                this.hideTypingIndicator();
                
                if (response.error) {
                    this.addMessage(`Error: ${response.error}`, 'system');
                    return;
                }

                // Add bot response with metadata
                this.addBotMessage(response);
            }
        } catch (error) {
            this.hideTypingIndicator();
            console.error('API Error:', error);
            this.addMessage('Sorry, I encountered an error. Please try again.', 'system');
        }
    }

    async callAPI(question) {
        const response = await fetch('/ask', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                question: question,
                session_id: this.currentSessionId
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return await response.json();
    }

    clearWelcomeMessage() {
        const welcomeMessage = document.querySelector('.welcome-message');
        if (welcomeMessage) {
            welcomeMessage.style.animation = 'fadeOut 0.3s ease-out forwards';
            setTimeout(() => {
                welcomeMessage.remove();
            }, 300);
        }
    }

    addMessage(content, type, metadata = null) {
        const messagesContainer = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;

        let messageHtml = `
            <div class="message-bubble">
                <div class="message-content">${this.formatMessage(content)}</div>
        `;

        // Add metadata for bot/assistant messages
        if ((type === 'bot' || type === 'assistant') && metadata) {
            const confidenceClass = `confidence-${metadata.confidence || 'medium'}`;
            messageHtml += `
                <div class="message-meta">
                    <div class="message-info">
                        <span class="confidence-badge ${confidenceClass}">${metadata.confidence || 'medium'}</span>
                        <span class="sources-count">${metadata.sourcesUsed || metadata.sources_used || 0} sources</span>
                    </div>
                    <div class="message-language">${metadata.language || 'English'}</div>
                </div>
            `;
        }

        messageHtml += `</div>`;
        messageDiv.innerHTML = messageHtml;

        messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    addBotMessage(response) {
        const content = response.answer || 'No response received';
        const metadata = {
            confidence: response.confidence,
            sources_used: response.sources ? response.sources.length : 0,
            language: response.language,
            is_follow_up: response.is_follow_up
        };

        this.addMessage(content, 'bot', metadata);

        // Show sources if available
        if (response.sources && response.sources.length > 0) {
            this.addSourcesMessage(response.sources);
        }
    }

    addSourcesMessage(sources) {
        const messagesContainer = document.getElementById('chatMessages');
        const sourceDiv = document.createElement('div');
        sourceDiv.className = 'message system';

        let sourcesHtml = '<div class="message-bubble"><div class="message-content">';
        sourcesHtml += '<strong>📚 Sources used:</strong><br>';
        sources.forEach((source, index) => {
            sourcesHtml += `${index + 1}. ${source}<br>`;
        });
        sourcesHtml += '</div></div>';

        sourceDiv.innerHTML = sourcesHtml;
        messagesContainer.appendChild(sourceDiv);
        this.scrollToBottom();
    }

    formatMessage(content) {
        // Simple formatting - convert line breaks and basic markdown
        return content
            .replace(/\n/g, '<br>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>');
    }

    showTypingIndicator() {
        this.isTyping = true;
        const messagesContainer = document.getElementById('chatMessages');
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message bot';
        typingDiv.id = 'typingIndicator';
        
        typingDiv.innerHTML = `
            <div class="typing-indicator">
                <div class="typing-dots">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;
        
        messagesContainer.appendChild(typingDiv);
        this.scrollToBottom();
        this.updateSendButton(true);
    }

    hideTypingIndicator() {
        this.isTyping = false;
        const typingIndicator = document.getElementById('typingIndicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
        this.updateSendButton(false);
    }

    updateSendButton(disabled) {
        const sendButton = document.getElementById('sendButton');
        sendButton.disabled = disabled;
    }

    scrollToBottom() {
        const messagesContainer = document.getElementById('chatMessages');
        setTimeout(() => {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }, 100);
    }

    async clearConversation() {
        if (confirm('Are you sure you want to clear the conversation?')) {
            try {
                // Call API to clear server-side conversation
                await fetch('/conversation/clear', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        session_id: this.currentSessionId
                    })
                });

                // Clear UI and reset
                this.generateSessionId();
                this.showWelcomeMessage();
                this.focusInput();

            } catch (error) {
                console.error('Error clearing conversation:', error);
                // Still clear UI even if API call fails
                this.generateSessionId();
                this.showWelcomeMessage();
                this.focusInput();
            }
        }
    }

    // Mode management methods
    changeMode(mode) {
        this.currentMode = mode;
        this.chatSessionActive = false;
        
        // Clear existing messages
        const messagesContainer = document.getElementById('chatMessages');
        messagesContainer.innerHTML = '';

        // Show mode change notification
        const modeNames = {
            'single': '🔍 Single Question Mode',
            'chat': '💬 Interactive Chat Mode',
            'demo': '🚀 Quick Demo Mode',
            'examples': '💡 Examples Mode'
        };
        
        this.addMessage(`Mode changed to: ${modeNames[mode]}`, 'system');

        switch(mode) {
            case 'single':
                this.showWelcomeMessage();
                break;
            case 'chat':
                this.startInteractiveChat();
                break;
            case 'demo':
                this.runDemo();
                break;
            case 'examples':
                this.showExamples();
                break;
        }
    }

    async startInteractiveChat() {
        this.addMessage('Starting interactive chat session...', 'system');
        
        try {
            const response = await fetch('/chat/start', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({})
            });

            const data = await response.json();
            
            if (data.session_id) {
                this.currentSessionId = data.session_id;
                this.chatSessionActive = true;
                
                this.addMessage(`✨ ${data.message}`, 'system');
                this.addMessage(`📝 ${data.instructions.description}`, 'system');
                this.addMessage(`🌍 Supported languages: ${data.instructions.supported_languages.join(', ')}`, 'system');
                this.addMessage(`💡 Commands: Type 'examples' for sample questions, 'quit' to end session`, 'system');
            }
        } catch (error) {
            this.addMessage(`❌ Error starting chat: ${error.message}`, 'system');
        }
    }

    async runDemo() {
        this.addMessage('🚀 Running Quick Multilingual Demo...', 'system');
        
        try {
            const response = await fetch('/demo', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });

            const data = await response.json();
            
            if (data.demo_results) {
                this.addMessage('🎉 Demo Results:', 'system');
                
                data.demo_results.forEach((result, index) => {
                    this.addMessage(`\n**${result.language} Question:**`, 'system');
                    this.addMessage(result.question, 'user');
                    
                    this.addMessage(`**Answer (${result.detected_language}):**`, 'system');
                    this.addMessage(result.answer, 'assistant', {
                        confidence: result.confidence,
                        sources: result.sources,
                        sourcesUsed: result.sources_used
                    });
                });
                
                this.addMessage('✅ Demo completed! The system can handle questions in multiple languages!', 'system');
            }
        } catch (error) {
            this.addMessage(`❌ Error running demo: ${error.message}`, 'system');
        }
    }

    async showExamples() {
        this.addMessage('💡 Loading multilingual examples...', 'system');
        
        try {
            const response = await fetch('/examples');
            const data = await response.json();
            
            if (data.examples) {
                this.addMessage('🌍 Example Questions in Multiple Languages:', 'system');
                this.addMessage(data.instructions, 'system');
                
                data.examples.forEach((example, index) => {
                    this.addClickableExample(`${index + 1}. [${example.language}] ${example.question}`, example.question);
                });
                
                this.addMessage('✨ Click on any example above to ask that question!', 'system');
            }
        } catch (error) {
            this.addMessage(`❌ Error loading examples: ${error.message}`, 'system');
        }
    }

    addClickableExample(displayText, questionText) {
        const messagesContainer = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message example-question';

        const messageHtml = `
            <div class="message-bubble clickable-example" data-question="${questionText.replace(/"/g, '&quot;')}">
                <div class="message-content">${this.formatMessage(displayText)}</div>
                <div class="click-hint">👆 Click to ask this question</div>
            </div>
        `;

        messageDiv.innerHTML = messageHtml;

        // Add click event listener
        const bubble = messageDiv.querySelector('.clickable-example');
        bubble.addEventListener('click', () => {
            const question = bubble.getAttribute('data-question');
            this.sendMessageWithText(question);
        });

        messagesContainer.appendChild(messageDiv);
        this.scrollToBottom();
    }

    async sendChatMessage(message) {
        try {
            const response = await fetch('/chat/message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    session_id: this.currentSessionId
                })
            });

            const data = await response.json();
            
            if (data.type === 'examples') {
                this.addMessage('💡 Example Questions:', 'system');
                data.examples.forEach((example, index) => {
                    this.addClickableExample(`${index + 1}. [${example.language}] ${example.question}`, example.question);
                });
            } else if (data.type === 'quit') {
                this.addMessage(data.message, 'system');
                this.chatSessionActive = false;
            } else if (data.type === 'answer') {
                this.addMessage(data.answer, 'assistant', {
                    confidence: data.confidence,
                    sources: data.sources,
                    sourcesUsed: data.sources_used,
                    language: data.language,
                    isFollowUp: data.is_follow_up
                });
            }
        } catch (error) {
            this.addMessage(`❌ Error: ${error.message}`, 'system');
        }
    }
}

// Initialize the chatbot when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new ChatBot();
});

// Add CSS animation for fade out
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeOut {
        from {
            opacity: 1;
            transform: translateY(0);
        }
        to {
            opacity: 0;
            transform: translateY(-20px);
        }
    }
`;
document.head.appendChild(style);
