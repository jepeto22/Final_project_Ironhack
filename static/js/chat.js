class ChatBot {
    constructor() {
        this.isTyping = false;
        this.currentSessionId = null;
        this.currentMode = 'single';
        this.currentPersonality = 'normal'; // Add personality tracking
        this.chatSessionActive = false;
        
        // Voice recording properties
        this.isRecording = false;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.recognition = null;
        this.speechSupported = false;
        
        this.init();
    }

    init() {
        this.bindEvents();
        this.generateSessionId();
        this.showWelcomeMessage();
        this.createParticles();
        this.focusInput();
        this.initializeSpeechRecognition();
        this.initializeTextToSpeech();
    }

    async initializeSpeechRecognition() {
        // Check for speech recognition support
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            try {
                const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
                this.recognition = new SpeechRecognition();
                
                this.recognition.continuous = false;
                this.recognition.interimResults = true;
                this.recognition.lang = 'en-US'; // Default language, can be changed
                this.recognition.maxAlternatives = 1;
                
                this.recognition.onstart = () => {
                    this.onVoiceRecordingStart();
                };
                
                this.recognition.onresult = (event) => {
                    this.onVoiceRecognitionResult(event);
                };
                
                this.recognition.onerror = (event) => {
                    this.onVoiceRecognitionError(event);
                };
                
                this.recognition.onend = () => {
                    this.onVoiceRecordingEnd();
                };
                
                // Check microphone permissions
                try {
                    await navigator.mediaDevices.getUserMedia({ audio: true });
                    this.speechSupported = true;
                    console.log('✅ Speech recognition and microphone access initialized');
                } catch (permissionError) {
                    console.warn('⚠️ Microphone permission not granted:', permissionError);
                    this.speechSupported = true; // Still allow trying, will show error when recording
                }
                
            } catch (error) {
                console.error('Error initializing speech recognition:', error);
                this.speechSupported = false;
            }
        } else {
            console.log('❌ Speech recognition not supported');
            this.speechSupported = false;
        }
        
        // Show/hide voice button based on support
        const voiceButton = document.getElementById('voiceButton');
        if (voiceButton) {
            if (this.speechSupported) {
                voiceButton.style.display = 'flex';
            } else {
                voiceButton.style.display = 'none';
                // Show fallback message
                console.log('💡 Voice recording not available. Please use text input.');
            }
        }
    }

    // Text-to-Speech functionality
    initializeTextToSpeech() {
        this.speechSynthesis = window.speechSynthesis;
        this.ttsEnabled = 'speechSynthesis' in window;
        this.availableVoices = [];
        this.preferredVoices = {};
        
        if (this.ttsEnabled) {
            // Load voices immediately and on change
            this.loadOptimalVoices();
            
            if (speechSynthesis.onvoiceschanged !== undefined) {
                speechSynthesis.onvoiceschanged = () => {
                    this.loadOptimalVoices();
                };
            }
            
            console.log('✅ Enhanced TTS initialized for natural speech');
        } else {
            console.log('❌ TTS not supported in this browser');
        }
    }

    loadOptimalVoices() {
        this.availableVoices = this.speechSynthesis.getVoices();
        this.selectBestVoicesForNaturalSpeech();
        console.log(`🎵 Loaded ${this.availableVoices.length} voices, selected optimal voices for natural speech`);
    }

    selectBestVoicesForNaturalSpeech() {
        // Clear previous selections
        this.preferredVoices = {};
        
        // Define what makes a voice sound natural and native
        const languageProfiles = {
            'en-US': {
                // Native English voices that sound most natural
                preferred: ['Samantha', 'Alex', 'Victoria', 'Google US English', 'Microsoft Zira'],
                fallback: (voice) => voice.lang.includes('en') && (voice.lang.includes('US') || voice.name.includes('US'))
            },
            'en-GB': {
                preferred: ['Daniel', 'Kate', 'Google UK English', 'Microsoft Hazel'],
                fallback: (voice) => voice.lang.includes('en') && (voice.lang.includes('GB') || voice.name.includes('UK'))
            },
            'es-ES': {
                preferred: ['Monica', 'Google español', 'Microsoft Helena'],
                fallback: (voice) => voice.lang.includes('es') && !voice.lang.includes('MX')
            },
            'es-MX': {
                preferred: ['Paulina', 'Google español de Estados Unidos', 'Microsoft Sabina'],
                fallback: (voice) => voice.lang.includes('es') && voice.lang.includes('MX')
            },
            'fr-FR': {
                preferred: ['Thomas', 'Google français', 'Microsoft Hortense'],
                fallback: (voice) => voice.lang.includes('fr')
            },
            'de-DE': {
                preferred: ['Anna', 'Google Deutsch', 'Microsoft Hedda'],
                fallback: (voice) => voice.lang.includes('de')
            },
            'it-IT': {
                preferred: ['Alice', 'Google italiano', 'Microsoft Elsa'],
                fallback: (voice) => voice.lang.includes('it')
            },
            'pt-BR': {
                preferred: ['Luciana', 'Google português do Brasil', 'Microsoft Maria'],
                fallback: (voice) => voice.lang.includes('pt') && voice.lang.includes('BR')
            }
        };

        for (const [langCode, profile] of Object.entries(languageProfiles)) {
            let selectedVoice = null;

            // First priority: Find exact matches from preferred list
            for (const preferredName of profile.preferred) {
                const voice = this.availableVoices.find(v => 
                    v.name.includes(preferredName) || v.name === preferredName
                );
                if (voice) {
                    selectedVoice = voice;
                    break;
                }
            }

            // Second priority: Use fallback logic
            if (!selectedVoice) {
                selectedVoice = this.availableVoices.find(profile.fallback);
            }

            // Third priority: Any voice for the language family
            if (!selectedVoice) {
                const langFamily = langCode.substring(0, 2);
                selectedVoice = this.availableVoices.find(voice => 
                    voice.lang.toLowerCase().startsWith(langFamily.toLowerCase())
                );
            }

            if (selectedVoice) {
                this.preferredVoices[langCode] = selectedVoice;
                console.log(`🎵 ${langCode}: ${selectedVoice.name} (${selectedVoice.localService ? 'native' : 'cloud'})`);
            }
        }
    }

    async speakText(text, language = 'en-US', customOptions = {}) {
        if (!this.ttsEnabled || !text || text.trim().length === 0) {
            console.log('❌ TTS not available or no text provided');
            return null;
        }

        // Stop any current speech
        this.speechSynthesis.cancel();
        
        // Clean and prepare text for natural speech
        const cleanedText = this.prepareTextForNaturalSpeech(text, language);
        console.log(`🎵 Speaking (${language}): "${cleanedText.substring(0, 50)}..."`);

        // Create speech utterance
        const utterance = new SpeechSynthesisUtterance(cleanedText);
        
        // Select the best voice available
        const selectedVoice = this.getOptimalVoiceForLanguage(language);
        if (selectedVoice) {
            utterance.voice = selectedVoice;
            console.log(`� Using voice: ${selectedVoice.name}`);
        } else {
            console.log(`⚠️ No optimal voice found for ${language}, using default`);
        }
        
        utterance.lang = language;
        
        // Apply natural speech parameters
        const speechConfig = this.getNaturalSpeechConfig(language);
        utterance.rate = customOptions.rate || speechConfig.rate;
        utterance.pitch = customOptions.pitch || speechConfig.pitch;
        utterance.volume = customOptions.volume || speechConfig.volume;

        // Add event handlers for better user experience
        utterance.onstart = () => {
            console.log('🔊 Natural speech started');
        };

        utterance.onend = () => {
            console.log('✅ Natural speech completed');
        };

        utterance.onerror = (event) => {
            console.error('❌ Speech synthesis error:', event.error, event.name);
        };

        // Speak with slight delay to ensure proper voice loading
        setTimeout(() => {
            this.speechSynthesis.speak(utterance);
        }, 100);
        
        return utterance;
    }

    getOptimalVoiceForLanguage(language) {
        // Try exact language match first
        if (this.preferredVoices[language]) {
            return this.preferredVoices[language];
        }
        
        // Try language family match (en-US -> en-GB, etc.)
        const languageFamily = language.substring(0, 2);
        for (const [code, voice] of Object.entries(this.preferredVoices)) {
            if (code.startsWith(languageFamily)) {
                return voice;
            }
        }
        
        // Fallback: find any voice that matches the language family
        return this.availableVoices.find(voice => 
            voice.lang.toLowerCase().startsWith(languageFamily.toLowerCase())
        ) || null;
    }

    prepareTextForNaturalSpeech(text, language) {
        // Start with basic cleanup
        let prepared = text
            // Remove markdown formatting
            .replace(/\*\*(.*?)\*\*/g, '$1')  // Bold
            .replace(/\*(.*?)\*/g, '$1')      // Italic
            .replace(/`(.*?)`/g, '$1')        // Inline code
            .replace(/_/g, ' ')               // Underscores
            // Fix spacing around punctuation
            .replace(/([.!?])\s*([A-Z])/g, '$1 $2')
            .replace(/,\s*/g, ', ')
            .replace(/:\s*/g, ': ')
            // Clean up multiple spaces
            .replace(/\s+/g, ' ')
            .trim();

        // Language-specific improvements for natural pronunciation
        if (language.startsWith('en')) {
            prepared = prepared
                .replace(/\bDr\./gi, 'Doctor')
                .replace(/\bMr\./gi, 'Mister')
                .replace(/\bMrs\./gi, 'Misses')
                .replace(/\bMs\./gi, 'Miss')
                .replace(/\betc\./gi, 'etcetera')
                .replace(/\be\.g\./gi, 'for example')
                .replace(/\bi\.e\./gi, 'that is')
                .replace(/\bvs\./gi, 'versus')
                .replace(/\bAI\b/gi, 'artificial intelligence')
                .replace(/\bCO2\b/gi, 'carbon dioxide')
                .replace(/\bDNA\b/gi, 'D-N-A')
                .replace(/\bRNA\b/gi, 'R-N-A')
                .replace(/\bCPU\b/gi, 'C-P-U')
                .replace(/\bGPU\b/gi, 'G-P-U')
                .replace(/\bURL\b/gi, 'U-R-L')
                .replace(/\bHTML\b/gi, 'H-T-M-L')
                .replace(/\bCSS\b/gi, 'C-S-S')
                .replace(/\bJS\b/gi, 'JavaScript');
        } else if (language.startsWith('es')) {
            prepared = prepared
                .replace(/\bDr\./gi, 'Doctor')
                .replace(/\bSr\./gi, 'Señor')
                .replace(/\bSra\./gi, 'Señora')
                .replace(/\betc\./gi, 'etcétera')
                .replace(/\bIA\b/gi, 'inteligencia artificial')
                .replace(/\bCO2\b/gi, 'dióxido de carbono');
        } else if (language.startsWith('fr')) {
            prepared = prepared
                .replace(/\bDr\./gi, 'Docteur')
                .replace(/\bM\./gi, 'Monsieur')
                .replace(/\bMme\./gi, 'Madame')
                .replace(/\betc\./gi, 'et cætera')
                .replace(/\bIA\b/gi, 'intelligence artificielle')
                .replace(/\bCO2\b/gi, 'dioxyde de carbone');
        }

        return prepared;
    }

    getNaturalSpeechConfig(language) {
        // Optimized configurations for the most natural-sounding speech
        const configs = {
            // English variants
            'en-US': { rate: 0.85, pitch: 1.0, volume: 0.9 },
            'en-GB': { rate: 0.8, pitch: 0.95, volume: 0.9 },
            
            // Spanish variants
            'es-ES': { rate: 0.85, pitch: 1.0, volume: 0.9 },
            'es-MX': { rate: 0.85, pitch: 1.0, volume: 0.9 },
            
            // Other languages
            'fr-FR': { rate: 0.8, pitch: 1.0, volume: 0.9 },
            'de-DE': { rate: 0.75, pitch: 0.95, volume: 0.9 },
            'it-IT': { rate: 0.85, pitch: 1.05, volume: 0.9 },
            'pt-BR': { rate: 0.85, pitch: 1.0, volume: 0.9 },
            'pt-PT': { rate: 0.8, pitch: 1.0, volume: 0.9 }
        };
        
        return configs[language] || configs['en-US'];
    }

    bindEvents() {
        const sendButton = document.getElementById('sendButton');
        const chatInput = document.getElementById('chatInput');
        const sampleQuestions = document.querySelectorAll('.sample-question');
        const clearButton = document.getElementById('clearButton');
        const modeSelect = document.getElementById('modeSelect');
        const personalitySelect = document.getElementById('personalitySelect');
        const voiceButton = document.getElementById('voiceButton');
        const cancelVoiceButton = document.getElementById('cancelVoice');
        const voiceSettingsButton = document.getElementById('voiceSettingsButton');

        // Mode selection
        if (modeSelect) {
            modeSelect.addEventListener('change', (e) => {
                this.changeMode(e.target.value);
            });
        }

        // Personality selection
        if (personalitySelect) {
            personalitySelect.addEventListener('change', (e) => {
                this.changePersonality(e.target.value);
            });
        }

        // Voice recording - Always bind the event, check support in the handler
        if (voiceButton) {
            voiceButton.addEventListener('click', () => this.toggleVoiceRecording());
            console.log('✅ Voice button event listener attached');
        } else {
            console.error('❌ Voice button not found in DOM');
        }

        if (cancelVoiceButton) {
            cancelVoiceButton.addEventListener('click', () => this.cancelVoiceRecording());
        }

        // Voice settings
        if (voiceSettingsButton) {
            voiceSettingsButton.addEventListener('click', () => this.showVoiceSettings());
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
                    <br><br>
                    💡 <strong>Try switching personality modes:</strong>
                    <br>🧠 <strong>Kurzgesagt Style:</strong> Educational and enthusiastic explanations
                    <br>🧪 <strong>Rick Sanchez Mode:</strong> Sarcastic genius scientist with attitude (*burp*)
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
                session_id: this.currentSessionId,
                mode: this.currentPersonality
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

    addMessage(content, type, metadata = null, isVoiceMessage = false) {
        const messagesContainer = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;

        // Add voice message class if applicable
        if (isVoiceMessage) {
            messageDiv.classList.add('voice-message');
        }

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

        // Add TTS button for bot responses
        this.addTTSButton(content, response.language || 'en-US');
    }

    addTTSButton(text, language) {
        if (!this.ttsEnabled) return;

        const messagesContainer = document.getElementById('chatMessages');
        const lastMessage = messagesContainer.lastElementChild;
        
        if (lastMessage && lastMessage.classList.contains('bot')) {
            const ttsButton = document.createElement('button');
            ttsButton.className = 'tts-button';
            ttsButton.innerHTML = '🎵 Listen';
            ttsButton.title = 'Listen to this response with natural speech';
            
            let currentUtterance = null;
            let isSpeaking = false;
            
            const handleTTSClick = async () => {
                if (isSpeaking) {
                    // Stop current speech
                    this.speechSynthesis.cancel();
                    if (currentUtterance) {
                        currentUtterance = null;
                    }
                    ttsButton.innerHTML = '🎵 Listen';
                    ttsButton.classList.remove('speaking');
                    isSpeaking = false;
                    return;
                }
                
                // Start natural speech
                ttsButton.innerHTML = '🔇 Stop';
                ttsButton.classList.add('speaking');
                isSpeaking = true;
                
                try {
                    // Get optimized speech parameters from server
                    const response = await fetch('/voice/speak', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            text: text,
                            language: language
                        })
                    });
                    
                    const ttsData = await response.json();
                    
                    // Use natural speech with server-optimized parameters
                    currentUtterance = await this.speakText(ttsData.text, language, {
                        rate: ttsData.speech_params.rate,
                        pitch: ttsData.speech_params.pitch,
                        volume: ttsData.speech_params.volume
                    });
                    
                    if (currentUtterance) {
                        currentUtterance.onend = () => {
                            ttsButton.innerHTML = '🎵 Listen';
                            ttsButton.classList.remove('speaking');
                            isSpeaking = false;
                            currentUtterance = null;
                        };
                        
                        currentUtterance.onerror = () => {
                            ttsButton.innerHTML = '🎵 Listen';
                            ttsButton.classList.remove('speaking');
                            isSpeaking = false;
                            currentUtterance = null;
                        };
                    }
                } catch (error) {
                    console.error('TTS Error:', error);
                    // Fallback to basic TTS
                    currentUtterance = await this.speakText(text, language);
                    ttsButton.innerHTML = '🎵 Listen';
                    ttsButton.classList.remove('speaking');
                    isSpeaking = false;
                }
            };
            
            ttsButton.addEventListener('click', handleTTSClick);

            const bubble = lastMessage.querySelector('.message-bubble');
            bubble.appendChild(ttsButton);
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

    changePersonality(personality) {
        this.currentPersonality = personality;
        
        // Show personality change notification
        const personalityNames = {
            'normal': '🧠 Kurzgesagt Style - Educational and enthusiastic science communication',
            'crazy_scientist': '🧪 Rick Sanchez Mode - Sarcastic genius scientist with burps and attitude'
        };
        
        this.addMessage(`Personality changed to: ${personalityNames[personality]}`, 'system');
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

    // Voice recording methods
    toggleVoiceRecording() {
        console.log('🎤 Toggle voice recording clicked');
        console.log('- speechSupported:', this.speechSupported);
        console.log('- recognition:', !!this.recognition);
        console.log('- isRecording:', this.isRecording);
        
        if (!this.speechSupported || !this.recognition) {
            console.log('❌ Voice recording not supported or not initialized');
            this.addMessage('❌ Voice recording is not supported in your browser. Please use Chrome, Safari, or Edge for voice features.', 'system');
            this.showBrowserCompatibilityInfo();
            return;
        }

        if (this.isRecording) {
            console.log('🛑 Stopping voice recording');
            this.stopVoiceRecording();
        } else {
            console.log('▶️ Starting voice recording');
            this.startVoiceRecording();
        }
    }

    showBrowserCompatibilityInfo() {
        const userAgent = navigator.userAgent;
        let browserInfo = '';
        
        if (userAgent.includes('Chrome')) {
            browserInfo = '💡 Chrome detected. Voice recording should work. Please ensure microphone permissions are enabled.';
        } else if (userAgent.includes('Safari')) {
            browserInfo = '💡 Safari detected. Voice recording should work. Please ensure microphone permissions are enabled.';
        } else if (userAgent.includes('Edge')) {
            browserInfo = '💡 Edge detected. Voice recording should work. Please ensure microphone permissions are enabled.';
        } else if (userAgent.includes('Firefox')) {
            browserInfo = '⚠️ Firefox detected. Voice recording may not be fully supported. Please try Chrome or Safari for best experience.';
        } else {
            browserInfo = '⚠️ Your browser may not support voice recording. Please try Chrome, Safari, or Edge for best experience.';
        }
        
        setTimeout(() => {
            this.addMessage(browserInfo, 'system');
        }, 1000);
    }

    async startVoiceRecording() {
        console.log('🎤 Starting voice recording...');
        
        if (this.isRecording) {
            console.log('⚠️ Already recording, ignoring request');
            return;
        }

        // Check if speech recognition is available
        if (!this.recognition) {
            console.error('❌ Speech recognition not initialized');
            this.addMessage('❌ Voice recording is not available. Please refresh the page and try again.', 'system');
            return;
        }

        // Check microphone permissions first
        try {
            console.log('🔍 Checking microphone permissions...');
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            console.log('✅ Microphone permission granted');
            stream.getTracks().forEach(track => track.stop()); // Stop the stream immediately
        } catch (error) {
            console.error('❌ Microphone permission error:', error);
            let message = '🎤 Microphone access denied. Please allow microphone access in your browser settings and refresh the page.';
            if (error.name === 'NotFoundError') {
                message = '🎤 No microphone found. Please connect a microphone and try again.';
            } else if (error.name === 'NotAllowedError') {
                message = '🚫 Microphone access denied. Please click the microphone icon in your browser address bar and allow access, then refresh the page.';
            } else if (error.name === 'NotReadableError') {
                message = '🎤 Microphone is already in use by another application. Please close other applications and try again.';
            }
            this.addMessage(message, 'system');
            return;
        }

        this.isRecording = true;
        this.audioChunks = [];

        // Update UI first
        this.updateVoiceRecordingUI(true);
        console.log('🎤 UI updated for recording state');

        try {
            // Start speech recognition
            console.log('🎤 Starting speech recognition...');
            this.recognition.start();
            this.addMessage('🎤 Listening... Please speak now', 'system');
        } catch (error) {
            console.error('❌ Error starting voice recording:', error);
            this.addMessage('❌ Could not start voice recording. Please try again.', 'system');
            this.onVoiceRecordingEnd();
        }
    }

    stopVoiceRecording() {
        if (!this.isRecording) return;

        try {
            this.recognition.stop();
        } catch (error) {
            console.error('Error stopping voice recording:', error);
        }
    }

    cancelVoiceRecording() {
        if (!this.isRecording) return;

        try {
            this.recognition.abort();
        } catch (error) {
            console.error('Error canceling voice recording:', error);
        }
        
        this.onVoiceRecordingEnd();
        this.addMessage('🚫 Voice recording canceled', 'system');
    }

    onVoiceRecordingStart() {
        document.getElementById('voiceStatusText').textContent = 'Listening... Speak now';
    }

    onVoiceRecognitionResult(event) {
        let interimTranscript = '';
        let finalTranscript = '';

        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            if (event.results[i].isFinal) {
                finalTranscript += transcript;
            } else {
                interimTranscript += transcript;
            }
        }

        // Update status with interim results
        if (interimTranscript) {
            document.getElementById('voiceStatusText').textContent = `Listening: "${interimTranscript}"`;
        }

        // If we have a final result, process it
        if (finalTranscript.trim()) {
            console.log('🎤 Voice recognition result:', finalTranscript);
            
            // Add the voice message to the chat
            this.addMessage(finalTranscript.trim(), 'user', null, true);
            
            // Send the message through the normal flow
            this.sendMessageWithText(finalTranscript.trim());
            
            this.onVoiceRecordingEnd();
        }
    }

    onVoiceRecognitionError(event) {
        console.error('Voice recognition error:', event.error, event);
        
        let errorMessage = 'Voice recognition error';
        let isRetryable = false;
        
        switch (event.error) {
            case 'no-speech':
                errorMessage = '🔇 No speech detected. Please try speaking again.';
                isRetryable = true;
                break;
            case 'audio-capture':
                errorMessage = '🎤 Microphone not accessible. Please check your microphone connection and browser permissions.';
                break;
            case 'not-allowed':
                errorMessage = '🚫 Microphone access denied. Please click the microphone icon in your browser address bar and allow access, then refresh the page.';
                break;
            case 'network':
                errorMessage = '🌐 Network error during voice recognition. Please check your internet connection.';
                isRetryable = true;
                break;
            case 'service-not-allowed':
                errorMessage = '🚫 Speech recognition service not allowed. Please check your browser settings.';
                break;
            case 'bad-grammar':
                errorMessage = '📝 Speech recognition grammar error. Please try again.';
                isRetryable = true;
                break;
            case 'language-not-supported':
                errorMessage = '🌍 Selected language not supported. Switching to English.';
                this.recognition.lang = 'en-US';
                isRetryable = true;
                break;
            case 'aborted':
                errorMessage = '🚫 Voice recording was canceled.';
                break;
            default:
                errorMessage = `❌ Voice recognition error: ${event.error}. Please try again.`;
                isRetryable = true;
        }
        
        this.addMessage(errorMessage, 'system');
        
        // For certain errors, suggest solutions
        if (event.error === 'not-allowed') {
            setTimeout(() => {
                this.addMessage('💡 To enable microphone access: Look for a microphone icon in your browser address bar and click "Allow", or check your browser settings under Privacy & Security > Microphone.', 'system');
            }, 1000);
        }
        
        this.onVoiceRecordingEnd();
    }

    onVoiceRecordingEnd() {
        this.isRecording = false;
        this.updateVoiceRecordingUI(false);
    }

    updateVoiceRecordingUI(recording) {
        const voiceButton = document.getElementById('voiceButton');
        const voiceStatus = document.getElementById('voiceStatus');
        const micIcon = document.getElementById('micIcon');
        const stopIcon = document.getElementById('stopIcon');

        if (recording) {
            voiceButton.classList.add('recording');
            voiceButton.title = 'Click to stop recording';
            voiceStatus.style.display = 'block';
            micIcon.style.display = 'none';
            stopIcon.style.display = 'block';
        } else {
            voiceButton.classList.remove('recording');
            voiceButton.title = 'Click to record voice message';
            voiceStatus.style.display = 'none';
            micIcon.style.display = 'block';
            stopIcon.style.display = 'none';
        }
    }

    // Debug and test methods
    testVoiceRecording() {
        console.log('🧪 Testing voice recording functionality...');
        
        // Check browser support
        console.log('Browser support check:');
        console.log('- webkitSpeechRecognition:', 'webkitSpeechRecognition' in window);
        console.log('- SpeechRecognition:', 'SpeechRecognition' in window);
        console.log('- navigator.mediaDevices:', !!navigator.mediaDevices);
        console.log('- getUserMedia:', !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia));
        
        // Check initialization state
        console.log('Initialization state:');
        console.log('- this.recognition:', !!this.recognition);
        console.log('- this.speechSupported:', this.speechSupported);
        console.log('- this.isRecording:', this.isRecording);
        
        // Test microphone permissions
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            navigator.mediaDevices.getUserMedia({ audio: true })
                .then(stream => {
                    console.log('✅ Microphone test successful');
                    stream.getTracks().forEach(track => track.stop());
                    this.addMessage('✅ Microphone test successful! Voice recording should work.', 'system');
                })
                .catch(error => {
                    console.error('❌ Microphone test failed:', error);
                    this.addMessage(`❌ Microphone test failed: ${error.message}`, 'system');
                });
        } else {
            console.error('❌ getUserMedia not supported');
            this.addMessage('❌ Microphone access not supported in this browser', 'system');
        }
    }
    setVoiceRecognitionLanguage(languageCode = 'en-US') {
        if (!this.recognition) return;

        // Use the language code directly if it's in the correct format
        const validLanguageCodes = [
            'en-US', 'es-ES', 'fr-FR', 'de-DE', 'it-IT', 'pt-PT',
            'zh-CN', 'ja-JP', 'ko-KR', 'ru-RU', 'ar-SA'
        ];

        if (validLanguageCodes.includes(languageCode)) {
            this.recognition.lang = languageCode;
        } else {
            // Fallback mapping for older format
            const languageMap = {
                'auto': 'en-US',
                'english': 'en-US',
                'spanish': 'es-ES',
                'french': 'fr-FR',
                'german': 'de-DE',
                'italian': 'it-IT',
                'portuguese': 'pt-PT',
                'chinese': 'zh-CN',
                'japanese': 'ja-JP',
                'korean': 'ko-KR',
                'russian': 'ru-RU',
                'arabic': 'ar-SA'
            };
            
            this.recognition.lang = languageMap[languageCode.toLowerCase()] || 'en-US';
        }
        
        console.log(`🌍 Voice recognition language set to: ${this.recognition.lang}`);
    }

    // Add language selector for voice input
    showLanguageSelector() {
        const languages = [
            { code: 'en-US', name: 'English (US)' },
            { code: 'es-ES', name: 'Español (España)' },
            { code: 'fr-FR', name: 'Français (France)' },
            { code: 'de-DE', name: 'Deutsch (Deutschland)' },
            { code: 'it-IT', name: 'Italiano (Italia)' },
            { code: 'pt-PT', name: 'Português (Portugal)' },
            { code: 'zh-CN', name: '中文 (简体)' },
            { code: 'ja-JP', name: '日本語 (日本)' },
            { code: 'ko-KR', name: '한국어 (대한민국)' },
            { code: 'ru-RU', name: 'Русский (Россия)' }
        ];

        let languageOptions = languages.map(lang => 
            `<option value="${lang.code}">${lang.name}</option>`
        ).join('');

        this.addMessage(`
            <div class="language-selector">
                <label for="voiceLangSelect">Select voice input language:</label>
                <select id="voiceLangSelect" onchange="chatBot.setVoiceRecognitionLanguage(this.value)">
                    ${languageOptions}
                </select>
            </div>
        `, 'system');
    }

    // Voice settings dialog
    async showVoiceSettings() {
        try {
            const response = await fetch('/voice/settings');
            const data = await response.json();

            // Get available voices info
            const voicesResponse = await fetch('/voice/available-voices');
            const voicesData = await voicesResponse.json();

            let languageOptions = data.supported_languages.map(lang => 
                `<option value="${lang.code}" ${lang.code === (this.recognition?.lang || 'en-US') ? 'selected' : ''}>
                    ${lang.name}
                </option>`
            ).join('');

            this.addMessage(`
                <div class="voice-settings-panel">
                    <h4>� Natural Voice Settings</h4>
                    
                    <div class="setting-group">
                        <label for="voiceLangSelect">Speech Language:</label>
                        <select id="voiceLangSelect" class="voice-lang-select">
                            ${languageOptions}
                        </select>
                    </div>
                    
                    <div class="setting-group">
                        <label>
                            <input type="checkbox" id="ttsEnabled" ${this.ttsEnabled ? 'checked' : ''}>
                            Enable natural text-to-speech for bot responses
                        </label>
                    </div>
                    
                    <div class="setting-group">
                        <label>
                            <input type="checkbox" id="autoTTS" checked>
                            Auto-speak new responses (recommended)
                        </label>
                    </div>
                    
                    <div class="setting-group">
                        <button id="testVoiceBtn" class="test-voice-btn">🎤 Test Voice Recording</button>
                        <button id="testTTSBtn" class="test-voice-btn">🎵 Test Natural Speech</button>
                        <button id="voiceInfoBtn" class="test-voice-btn">ℹ️ Voice Tips</button>
                    </div>
                    
                    <div class="setting-group">
                        <button id="saveVoiceSettings" class="save-settings-btn">💾 Save Settings</button>
                    </div>
                    
                    <p style="font-size: 12px; color: #888; margin-top: 12px;">
                        💡 For best results, use Chrome or Safari with a good internet connection.
                        The system automatically selects the most natural voice for your language.
                    </p>
                </div>
            `, 'system');

            // Add event listeners for the settings panel
            setTimeout(() => {
                const langSelect = document.getElementById('voiceLangSelect');
                const ttsCheckbox = document.getElementById('ttsEnabled');
                const ttsQuality = document.getElementById('ttsQuality');
                const speechRate = document.getElementById('speechRate');
                const autoTTS = document.getElementById('autoTTS');
                const testVoiceBtn = document.getElementById('testVoiceBtn');
                const testTTSBtn = document.getElementById('testTTSBtn');
                const voiceInfoBtn = document.getElementById('voiceInfoBtn');
                const saveBtn = document.getElementById('saveVoiceSettings');

                if (langSelect) {
                    langSelect.addEventListener('change', (e) => {
                        this.setVoiceRecognitionLanguage(e.target.value);
                    });
                }

                if (testVoiceBtn) {
                    testVoiceBtn.addEventListener('click', async () => {
                        await this.testVoiceRecording();
                    });
                }

                if (testTTSBtn) {
                    testTTSBtn.addEventListener('click', async () => {
                        const lang = langSelect?.value || 'en-US';
                        
                        // Get optimized TTS settings from server
                        try {
                            const ttsResponse = await fetch('/voice/speak', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({
                                    text: 'This is a test of natural text-to-speech. Listen to how clear and natural this sounds compared to robotic speech.',
                                    language: lang
                                })
                            });
                            
                            const ttsData = await ttsResponse.json();
                            
                            // Use optimized client-side TTS with server-provided parameters
                            await this.speakText(ttsData.text, lang, {
                                rate: ttsData.speech_params.rate,
                                pitch: ttsData.speech_params.pitch,
                                volume: ttsData.speech_params.volume
                            });
                            
                            this.addMessage(`✅ TTS Test completed using ${ttsData.message}`, 'system');
                            
                        } catch (error) {
                            console.error('TTS test error:', error);
                            // Fallback to basic TTS
                            await this.speakText('This is a fallback test of text-to-speech.', lang);
                        }
                    });
                }

                if (voiceInfoBtn) {
                    voiceInfoBtn.addEventListener('click', () => {
                        this.showVoiceInfo(voicesData);
                    });
                }

                if (saveBtn) {
                    saveBtn.addEventListener('click', () => {
                        this.saveVoiceSettings();
                    });
                }
            }, 100);

        } catch (error) {
            this.addMessage('❌ Error loading voice settings', 'system');
            console.error('Error loading voice settings:', error);
        }
    }

    showVoiceInfo(voicesData) {
        const currentLang = this.recognition?.lang || 'en-US';
        const recommendations = voicesData.voice_recommendations[currentLang] || voicesData.voice_recommendations['en-US'];
        
        let infoHtml = `
            <div class="voice-info-panel">
                <h4>🎵 Voice Quality Information</h4>
                
                <p><strong>Current Language:</strong> ${currentLang}</p>
                
                <p><strong>Recommended Voices:</strong></p>
                <ul>
        `;
        
        recommendations.preferred.forEach(voice => {
            infoHtml += `<li>${voice}</li>`;
        });
        
        infoHtml += `
                </ul>
                
                <p><strong>Optimal Settings:</strong></p>
                <ul>
                    <li>Rate: ${recommendations.settings.rate}x</li>
                    <li>Pitch: ${recommendations.settings.pitch}</li>
                    <li>Volume: ${recommendations.settings.volume}</li>
                </ul>
                
                <p><strong>Quality Tips:</strong></p>
                <ul>
        `;
        
        voicesData.quality_tips.forEach(tip => {
            infoHtml += `<li>${tip}</li>`;
        });
        
        infoHtml += `
                </ul>
            </div>
        `;
        
        this.addMessage(infoHtml, 'system');
    }

    async testVoiceRecording() {
        this.addMessage('🔍 Testing voice recording capabilities...', 'system');
        
        // Test 1: Check browser support
        const hasWebkitSpeech = 'webkitSpeechRecognition' in window;
        const hasSpeech = 'SpeechRecognition' in window;
        const hasMediaDevices = 'mediaDevices' in navigator;
        const hasGetUserMedia = hasMediaDevices && 'getUserMedia' in navigator.mediaDevices;
        
        this.addMessage(`🌐 Browser Support:
• webkitSpeechRecognition: ${hasWebkitSpeech ? '✅' : '❌'}
• SpeechRecognition: ${hasSpeech ? '✅' : '❌'}
• MediaDevices API: ${hasMediaDevices ? '✅' : '❌'}
• getUserMedia: ${hasGetUserMedia ? '✅' : '❌'}`, 'system');
        
        // Test 2: Check microphone access
        if (hasGetUserMedia) {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                this.addMessage('🎤 Microphone access: ✅ Granted', 'system');
                stream.getTracks().forEach(track => track.stop());
                
                // Test 3: Check available audio devices
                const devices = await navigator.mediaDevices.enumerateDevices();
                const audioInputs = devices.filter(device => device.kind === 'audioinput');
                this.addMessage(`🎙️ Audio input devices found: ${audioInputs.length}`, 'system');
                
            } catch (error) {
                this.addMessage(`🚫 Microphone access: ❌ ${error.name} - ${error.message}`, 'system');
                return;
            }
        }
        
        // Test 4: Try to initialize speech recognition
        if (this.speechSupported && this.recognition) {
            this.addMessage('🗣️ Speech recognition initialized: ✅', 'system');
            this.addMessage('🎤 Now say something to test voice recognition...', 'system');
            
            // Start recording with additional error handling
            try {
                this.startVoiceRecording();
            } catch (error) {
                this.addMessage(`❌ Error starting voice recording: ${error.message}`, 'system');
            }
        } else {
            this.addMessage('❌ Speech recognition not available', 'system');
        }
    }

    async saveVoiceSettings() {
        const langSelect = document.getElementById('voiceLangSelect');
        const ttsCheckbox = document.getElementById('ttsEnabled');

        if (langSelect) {
            try {
                await fetch('/voice/settings', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        language: langSelect.value,
                        tts_enabled: ttsCheckbox?.checked || false
                    })
                });

                this.addMessage('✅ Voice settings saved successfully!', 'system');
            } catch (error) {
                this.addMessage('❌ Error saving voice settings', 'system');
                console.error('Error saving voice settings:', error);
            }
        }
    }
}

// Initialize the chatbot when the page loads
document.addEventListener('DOMContentLoaded', () => {
    // Initialize the chatbot and make it globally available for debugging
    window.chatBot = new ChatBot();
    
    // Add global debug functions
    window.testVoice = () => window.chatBot.testVoiceRecording();
    window.debugVoice = () => {
        console.log('Voice Debug Info:');
        console.log('- speechSupported:', window.chatBot.speechSupported);
        console.log('- recognition:', !!window.chatBot.recognition);
        console.log('- isRecording:', window.chatBot.isRecording);
    };
    
    console.log('🚀 ChatBot initialized. Use testVoice() or debugVoice() in console for debugging.');
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
