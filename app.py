"""
Kurzgesagt RAG Chatbot Flask App
Web interface and API for the Kurzgesagt Retrieval-Augmented Generation chatbot.
"""

import os
import uuid
import logging
import io
import base64
import re
import types
from tempfile import NamedTemporaryFile
from flask import Flask, request, jsonify, session, render_template, send_file
from dotenv import load_dotenv
import requests
from pydub import AudioSegment
from src.kurzgesagt_rag_agent import KurzgesagtRAGAgent

# ElevenLabs imports with error handling
try:
    from elevenlabs.client import ElevenLabs
    from elevenlabs import voices
    ELEVENLABS_CLIENT_AVAILABLE = True
except ImportError:
    ElevenLabs = None
    voices = None
    ELEVENLABS_CLIENT_AVAILABLE = False

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ElevenLabs configuration
try:
    ELEVENLABS_AVAILABLE = True
    logger.info("%s", "✅ ElevenLabs library available")
except ImportError:
    ELEVENLABS_AVAILABLE = False
    logger.warning("%s", "⚠️ ElevenLabs library not available - "
                         "install with: pip install elevenlabs")

ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
# Default Bella voice
ELEVENLABS_VOICE_ID = os.getenv('ELEVENLABS_VOICE_ID', 'EXAVITQu4vr4xnSDxMaL')
# Custom Rick voice ID
RICK_VOICE_ID = os.getenv('RICK_VOICE_ID', ELEVENLABS_VOICE_ID)
# Custom Kurzgesagt voice ID
KURZGESAGT_VOICE_ID = os.getenv('KURZGESAGT_VOICE_ID', ELEVENLABS_VOICE_ID)

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'kurzgesagt-rag-secret-key-2025')

# Initialize RAG agent with error handling
try:
    RAG_AGENT = KurzgesagtRAGAgent()
    logger.info("%s", "✅ Kurzgesagt RAG Agent initialized successfully")
except Exception as e:  # Broad exception needed for initialization errors
    logger.error("❌ Failed to initialize RAG Agent: %s", e)
    RAG_AGENT = None

def get_session_id():
    """Get or create session ID for conversation tracking."""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return session['session_id']

@app.route('/')
def index():
    """Serve the main chat interface."""
    return render_template('index.html')

@app.route('/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "agent_available": RAG_AGENT is not None,
        "version": "1.0.0"
    })

def is_english_language(language):
    """Check if the detected language is English."""
    return (language and
            (language.lower().startswith('en') or
             language.lower() == 'english'))

def validate_request_data(data):
    """Validate and extract request data."""
    if not data:
        return None, "No JSON data provided", 400

    question = data.get('question', '').strip()
    if not question:
        return None, "Question is required", 400

    session_id = data.get('session_id') or get_session_id()
    mode = data.get('mode', 'normal')

    return {
        'question': question,
        'session_id': session_id,
        'mode': mode
    }, None, None

def format_structured_response(answer_data, matches, language, session_id, mode):
    """Format structured response from RAG agent."""
    detected_language = answer_data.get('language', language)
    tts_available = is_english_language(detected_language)

    return {
        "answer": answer_data.get('answer', 'No answer available'),
        "confidence": answer_data.get('confidence', 'medium'),
        "sources": answer_data.get('sources', []),
        "sources_used": answer_data.get('sources_used', len(matches)),
        "language": detected_language,
        "session_id": session_id,
        "is_follow_up": answer_data.get('is_follow_up', False),
        "mode": mode,
        "tts_available": tts_available
    }

def format_simple_response(answer_data, matches, language, session_id, mode):
    """Format simple response for fallback cases."""
    tts_available = is_english_language(language)

    return {
        "answer": str(answer_data),
        "confidence": "medium",
        "sources": [match.metadata.get('video_title', 'Unknown')
                   for match in matches],
        "sources_used": len(matches),
        "language": language,
        "session_id": session_id,
        "is_follow_up": False,
        "mode": mode,
        "tts_available": tts_available
    }

@app.route('/ask', methods=['POST'])
def ask_question():
    """Process user questions and return AI responses."""
    if not RAG_AGENT:
        return jsonify({
            "error": "RAG Agent not available. Please check server configuration."
        }), 503

    try:
        data = request.get_json()
        validated_data, error_msg, error_code = validate_request_data(data)

        if error_msg:
            return jsonify({"error": error_msg}), error_code

        question = validated_data['question']
        session_id = validated_data['session_id']
        mode = validated_data['mode']

        logger.info("Processing question from session %s in %s mode...",
                   session_id[:8], mode)

        # Generate answer using RAG agent with specified mode
        result = RAG_AGENT.generate_answer(question, session_id, mode=mode)

        if isinstance(result, tuple) and len(result) >= 3:
            answer_data, matches, language = result
        else:
            return jsonify({"error": "Invalid response format from RAG agent"}), 500

        # Format response based on data type
        if isinstance(answer_data, dict):
            response = format_structured_response(
                answer_data, matches, language, session_id, mode
            )
        else:
            response = format_simple_response(
                answer_data, matches, language, session_id, mode
            )

        logger.info("Successfully processed question with confidence: %s",
                   response['confidence'])
        return jsonify(response)

    except Exception as e:  # Broad exception needed for error handling
        logger.error("Error processing question: %s", e)
        return jsonify({
            "error": f"An error occurred while processing your question: {str(e)}"
        }), 500

@app.route('/conversation/context', methods=['GET'])
def get_conversation_context():
    """Get current conversation context for a session."""
    if not RAG_AGENT:
        return jsonify({"error": "RAG Agent not available"}), 503

    try:
        session_id = request.args.get('session_id') or get_session_id()
        context = RAG_AGENT.get_conversation_context(session_id)

        return jsonify({
            "session_id": session_id,
            "context": context
        })
    except Exception as e:  # Broad exception needed for error handling
        logger.error("Error getting conversation context: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route('/conversation/clear', methods=['POST'])
def clear_conversation():
    """Clear conversation history for a session."""
    if not RAG_AGENT:
        return jsonify({"error": "RAG Agent not available"}), 503

    try:
        data = request.get_json()
        session_id = data.get('session_id') if data else get_session_id()

        RAG_AGENT.clear_conversation(session_id)

        return jsonify({
            "message": "Conversation cleared successfully",
            "session_id": session_id
        })
    except Exception as e:  # Broad exception needed for error handling
        logger.error("Error clearing conversation: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route('/stats')
def get_stats():
    """Get system statistics."""
    if not RAG_AGENT:
        return jsonify({"error": "RAG Agent not available"}), 503

    try:
        # Get memory stats
        memory_stats = RAG_AGENT.get_memory_stats()

        # Get index stats
        index_stats = RAG_AGENT.index.describe_index_stats()

        return jsonify({
            "memory_stats": memory_stats,
            "knowledge_base": {
                "total_vectors": index_stats.total_vector_count,
                "dimension": index_stats.dimension
            },
            "agent_status": "online"
        })
    except Exception as e:  # Broad exception needed for error handling
        logger.error("Error getting stats: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route('/modes', methods=['GET'])
def get_available_modes():
    """Get available conversation modes."""
    return jsonify({
        "modes": [
            {
                "id": "normal",
                "name": "Kurzgesagt Style",
                "description": "Educational and enthusiastic science communication",
                "emoji": "🧠"
            },
            {
                "id": "crazy_scientist",
                "name": "Rick Sanchez Mode",
                "description": "Sarcastic genius scientist with burps and attitude",
                "emoji": "🧪"
            }
        ]
    })



@app.route('/chat/start', methods=['POST'])
def start_chat():
    """Start an interactive chat session."""
    if not RAG_AGENT:
        return jsonify({"error": "RAG Agent not available"}), 503

    try:
        session_id = str(uuid.uuid4())

        return jsonify({
            "session_id": session_id,
            "message": "Interactive chat session started",
            "instructions": {
                "description": ("Ask questions in any language - "
                              "answers will be in the same language!"),
                "supported_languages": ["English", "Spanish", "French", "German",
                                       "Italian", "Portuguese", "etc."],
                "commands": {
                    "examples": "Type 'examples' to see sample questions",
                    "quit": "Type 'quit' to end the session"
                }
            }
        })

    except Exception as e:  # Broad exception needed for error handling
        logger.error("Error starting chat: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route('/chat/message', methods=['POST'])
def chat_message():
    """Send a message in the chat session."""
    if not RAG_AGENT:
        return jsonify({"error": "RAG Agent not available"}), 503

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        message = data.get('message', '').strip()
        session_id = data.get('session_id', str(uuid.uuid4()))
        mode = data.get('mode', 'normal')  # Ensure mode is tracked in chat

        if not message:
            return jsonify({"error": "Message is required"}), 400

        # Handle special commands
        if message.lower() == 'examples':
            examples = get_multilingual_examples()
            return jsonify({
                "type": "examples",
                "examples": examples,
                "session_id": session_id,
                "mode": mode  # Include mode for consistency
            })

        if message.lower() in ['quit', 'exit', 'q']:
            return jsonify({
                "type": "quit",
                "message": "Thanks for exploring science with Kurzgesagt RAG!",
                "session_id": session_id,
                "mode": mode  # Include mode for consistency
            })

        # Process the question
        result = RAG_AGENT.generate_answer(message, session_id, mode=mode)

        if isinstance(result, tuple) and len(result) >= 3:
            answer_data, matches, language = result
        else:
            return jsonify({"error": "Invalid response format from RAG agent"}), 500

        # Extract structured response
        if isinstance(answer_data, dict):
            detected_language = answer_data.get('language', language)
            tts_available = (detected_language and
                           (detected_language.lower().startswith('en') or
                            detected_language.lower() == 'english'))
            response = {
                "type": "answer",
                "question": message,
                "answer": answer_data.get('answer', 'No answer available'),
                "confidence": answer_data.get('confidence', 'medium'),
                "sources": answer_data.get('sources', []),
                "sources_used": answer_data.get('sources_used', len(matches)),
                "language": detected_language,
                "session_id": session_id,
                "is_follow_up": answer_data.get('is_follow_up', False),
                "tts_available": tts_available,
                "mode": mode  # Add mode to response
            }
        else:
            # Fallback for simple string responses
            # Only enable TTS for English responses
            tts_available = (language and
                           (language.lower().startswith('en') or
                            language.lower() == 'english'))
            response = {
                "type": "answer",
                "question": message,
                "answer": str(answer_data),
                "confidence": "medium",
                "sources": [match.metadata.get('video_title', 'Unknown')
                           for match in matches],
                "sources_used": len(matches),
                "language": language,
                "session_id": session_id,
                "is_follow_up": False,
                "tts_available": tts_available,
                "mode": mode  # Add mode to response
            }

        return jsonify(response)

    except Exception as e:  # Broad exception needed for error handling
        logger.error("Error processing chat message: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route('/examples')
def get_examples():
    """Get multilingual example questions."""
    examples = get_multilingual_examples()
    return jsonify({
        "examples": examples,
        "instructions": ("You can ask questions in any language you're comfortable with! "
                        "The system will detect your language and respond accordingly.")
    })

def get_multilingual_examples():
    """Get example questions in multiple languages."""
    return [
        {"language": "English", "question": "How does the immune system protect us from diseases?"},
        {"language": "Spanish", "question": "¿Cómo funciona el sistema inmunológico?"},
        {"language": "French", "question": "Comment fonctionne le système immunitaire?"},
        {"language": "German", "question": "Wie funktioniert das Immunsystem?"},
        {"language": "Italian", "question": "Come funziona il sistema immunitario?"},
        {"language": "Portuguese", "question": "Como funciona o sistema imunológico?"},
        {"language": "English", "question": "What happens inside a black hole?"},
        {"language": "Spanish",
         "question": "¿Qué pasaría si la Tierra se convirtiera en un planeta errante?"},
        {"language": "French", "question": "Que se passe-t-il dans un trou noir?"},
        {"language": "German", "question": "Was passiert in einem schwarzen Loch?"},
        {"language": "English", "question": "Why should we worry about nuclear war?"},
        {"language": "Spanish",
         "question": "¿Por qué deberíamos preocuparnos por la guerra nuclear?"}
    ]

@app.errorhandler(404)
def not_found(_error):
    """Handle 404 errors."""
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error("Internal server error: %s", error)
    return jsonify({"error": "Internal server error"}), 500

class TTSConfig:
    """Configuration for TTS generation."""
    def __init__(self, cleaned_text, original_text, language, provider, voice_id):
        self.cleaned_text = cleaned_text
        self.original_text = original_text
        self.language = language
        self.provider = provider
        self.voice_id = voice_id

def create_tts_response(tts_config, message):
    """Create TTS response with cleaned text."""
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    audio = None

    # Try the latest SDK method first
    if hasattr(client, 'tts') and callable(client.tts):
        try:
            audio = client.tts(
                text=tts_config.cleaned_text,
                voice=tts_config.voice_id,
                model="eleven_multilingual_v2"
            )
        except TypeError as e:
            logger.warning("[TTS] 'tts' did not accept 'voice' or 'model', "
                          "trying alternatives: %s", e)
            try:
                audio = client.tts(
                    text=tts_config.cleaned_text,
                    voice=tts_config.voice_id
                )
            except TypeError as e2:
                logger.warning("[TTS] 'tts' did not accept 'voice', "
                              "trying 'voice_id': %s", e2)
                try:
                    audio = client.tts(
                        text=tts_config.cleaned_text,
                        voice_id=tts_config.voice_id,
                        model="eleven_multilingual_v2"
                    )
                except TypeError as e3:
                    logger.warning("[TTS] 'tts' did not accept 'voice_id' or "
                                  "'model', trying without 'model': %s", e3)
                    audio = client.tts(
                        text=tts_config.cleaned_text,
                        voice_id=tts_config.voice_id
                    )
    elif (hasattr(client, 'text_to_speech') and
          hasattr(client.text_to_speech, 'convert') and
          callable(client.text_to_speech.convert)):
        try:
            audio = client.text_to_speech.convert(
                text=tts_config.cleaned_text,
                voice_id=tts_config.voice_id
            )
        except Exception as e:
            logger.error("[TTS] ElevenLabs convert() failed: %s", e)
            return jsonify({
                "error": f"ElevenLabs TTS failed: {e}",
                "tts_provider": "elevenlabs",
                "voice_id": tts_config.voice_id
            }), 500
    else:
        logger.error("No compatible ElevenLabs TTS method found in SDK. "
                    "Please update the elevenlabs package.")
        return jsonify({
            "error": ("No compatible ElevenLabs TTS method found in SDK. "
                     "Please update the elevenlabs package."),
            "tts_provider": "elevenlabs",
            "voice_id": tts_config.voice_id
        }), 500

    if isinstance(audio, (types.GeneratorType, list, tuple)) or hasattr(audio, '__iter__'):
        audio_bytes = b''.join(
            chunk if isinstance(chunk, bytes) else bytes(chunk)
            for chunk in audio
        )
    else:
        audio_bytes = audio

    audio_base64 = base64.b64encode(audio_bytes).decode('utf-8')
    return jsonify({
        "text": tts_config.cleaned_text,
        "original_text": tts_config.original_text,
        "language": tts_config.language,
        "audio_base64": audio_base64,
        "audio_format": "mp3",
        "provider": tts_config.provider,
        "voice_id": tts_config.voice_id,
        "message": message
    })

def determine_voice_config(mode, language):
    """Determine voice configuration based on mode and language."""
    is_english = (language.lower().startswith('en') or
                 language.lower() == 'english')
    mode_clean = (mode or '').strip().lower()

    if mode_clean == 'crazy_scientist':
        voice_id = RICK_VOICE_ID
        provider = 'elevenlabs_rick'
    elif mode_clean == 'normal':
        voice_id = KURZGESAGT_VOICE_ID
        provider = 'elevenlabs_kurzgesagt'
    else:
        voice_id = ELEVENLABS_VOICE_ID
        provider = 'elevenlabs'

    return voice_id, provider, is_english

def handle_rick_burp_tts(text, voice_id, provider, language):
    """Handle Rick mode TTS with burp sound effects."""
    cleaned_text = clean_text_for_natural_speech(text, language)
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    logger.info('[TTS] Rick mode: inserting burp sound for \'burp\' marker')

    # Split text on 'burp' (case-insensitive, keep delimiter)
    parts = re.split(r'(\bburp\b)', cleaned_text, flags=re.IGNORECASE)
    segments = []
    burp_path = os.path.join(app.root_path, 'static', 'audio', 'burp.mp3')
    burp_audio = AudioSegment.from_file(burp_path, format='mp3')

    for part in parts:
        if re.match(r'\bburp\b', part, re.IGNORECASE):
            segments.append(burp_audio)
        else:
            seg = part.strip()
            if seg:
                try:
                    tts_audio = None
                    if hasattr(client, 'tts') and callable(client.tts):
                        try:
                            tts_audio = client.tts(
                                text=seg,
                                voice=voice_id,
                                model="eleven_multilingual_v2"
                            )
                        except TypeError:
                            tts_audio = client.tts(text=seg, voice=voice_id)
                    elif (hasattr(client, 'text_to_speech') and
                          hasattr(client.text_to_speech, 'convert') and
                          callable(client.text_to_speech.convert)):
                        tts_audio = client.text_to_speech.convert(
                            text=seg, voice_id=voice_id
                        )

                    if (isinstance(tts_audio, (types.GeneratorType, list, tuple)) or
                        hasattr(tts_audio, '__iter__')):
                        tts_bytes = b''.join(
                            chunk if isinstance(chunk, bytes) else bytes(chunk)
                            for chunk in tts_audio
                        )
                    else:
                        tts_bytes = tts_audio

                    tts_segment = AudioSegment.from_file(
                        io.BytesIO(tts_bytes), format='mp3'
                    )
                    segments.append(tts_segment)
                except Exception as e:
                    logger.error("[TTS] Error generating TTS for segment: %s", e)

    if not segments:
        return None

    combined = segments[0]
    for seg in segments[1:]:
        combined += seg

    out_buffer = io.BytesIO()
    combined.export(out_buffer, format='mp3')
    audio_base64 = base64.b64encode(out_buffer.getvalue()).decode('utf-8')

    return {
        "text": cleaned_text,
        "original_text": text,
        "language": language,
        "audio_base64": audio_base64,
        "audio_format": "mp3",
        "provider": provider,
        "voice_id": voice_id,
        "message": "High-quality Rick TTS with burp sound(s)"
    }

@app.route('/voice/speak', methods=['POST'])
def text_to_speech():
    """Generate natural text-to-speech for responses."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        text = data.get('text', '').strip()
        language = data.get('language', 'en-US')
        mode = data.get('mode', 'normal')

        if not text:
            return jsonify({"error": "Text is required"}), 400

        voice_id, provider, is_english = determine_voice_config(mode, language)

        logger.info("[TTS] Requested mode: %s, language: %s", mode, language)
        logger.info("[TTS] Using voice_id: %s (provider: %s)", voice_id, provider)

        mode_clean = (mode or '').strip().lower()

        if is_english and ELEVENLABS_AVAILABLE:
            # Rick mode: handle 'burp' as a sound effect
            if (mode_clean == 'crazy_scientist' and
                re.search(r'\bburp\b', text, re.IGNORECASE)):

                result = handle_rick_burp_tts(text, voice_id, provider, language)
                if result:
                    return jsonify(result)
                
                return jsonify({
                    "error": "No audio segments generated for Rick TTS with burp."
                }), 500

            # Standard ElevenLabs TTS
            try:
                cleaned_text = clean_text_for_natural_speech(text, language)
                message = (f"High-quality ElevenLabs voice synthesis for "
                          f"{get_language_name(language)}")

                tts_config = TTSConfig(
                    cleaned_text, text, language, provider, voice_id
                )
                return create_tts_response(tts_config, message)
            except Exception as e:  # Broad exception needed for TTS errors
                logger.error("ElevenLabs TTS error: %s", e)
                return jsonify({
                    "error": f"ElevenLabs TTS error: {e}",
                    "tts_provider": "elevenlabs",
                    "voice_id": voice_id
                }), 500

        # Fallback to browser-based TTS for non-English or if ElevenLabs is not available
        cleaned_text = clean_text_for_natural_speech(text, language)
        best_voice = get_best_voice_for_language(language)
        return jsonify({
            "text": cleaned_text,
            "original_text": text,
            "language": language,
            "provider": "browser",
            "client_tts": True,
            "voice_preference": best_voice,
            "message": f"Optimized for natural {get_language_name(language)} speech"
        })
    except Exception as e:  # Broad exception needed for error handling
        logger.error("Error in text-to-speech: %s", e)
        return jsonify({"error": str(e)}), 500

def clean_text_for_natural_speech(text, language):
    """Clean text for natural, native-like speech synthesis."""

    # Basic cleaning that works for all languages
    cleaned = text

    # Remove markdown and formatting
    cleaned = re.sub(r'\*\*(.*?)\*\*', r'\1', cleaned)  # Bold
    cleaned = re.sub(r'\*(.*?)\*', r'\1', cleaned)      # Italic
    cleaned = re.sub(r'`(.*?)`', r'\1', cleaned)        # Code

    # Handle common abbreviations by language
    if language.startswith('en'):
        cleaned = re.sub(r'\bDr\.', 'Doctor', cleaned)
        cleaned = re.sub(r'\bMr\.', 'Mister', cleaned)
        cleaned = re.sub(r'\bMrs\.', 'Missus', cleaned)
        cleaned = re.sub(r'\betc\.', 'etcetera', cleaned)
        cleaned = re.sub(r'\bAI\b', 'artificial intelligence', cleaned)
        cleaned = re.sub(r'\bDNA\b', 'DNA', cleaned)  # Keep as-is, sounds better
        cleaned = re.sub(r'\bCO2\b', 'carbon dioxide', cleaned)

    # Add natural pauses (keep it simple)
    cleaned = re.sub(r'([.!?])\s+', r'\1 ', cleaned)
    cleaned = re.sub(r',\s*', ', ', cleaned)
    cleaned = re.sub(r':\s*', ': ', cleaned)

    # Clean up spacing
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    return cleaned

def get_language_name(language_code):
    """Get human-readable language name."""
    names = {
        'en-US': 'American English',
        'en-GB': 'British English',
        'es-ES': 'Spanish (Spain)',
        'es-MX': 'Spanish (Mexico)',
        'fr-FR': 'French',
        'de-DE': 'German',
        'it-IT': 'Italian',
        'pt-BR': 'Portuguese (Brazil)',
        'pt-PT': 'Portuguese (Portugal)'
    }
    return names.get(language_code, language_code)

def get_best_voice_for_language(language):
    """Return the most natural and appropriate voice name for English only."""
    voice_mapping = {
        'en-US': 'Google US English',
    }
    return voice_mapping.get(language, 'Google US English')

@app.route('/voice/available-voices', methods=['GET'])
def get_available_voices():
    """Get information about optimal TTS voices for natural speech (English only)."""
    try:
        voice_recommendations = {
            'en-US': {
                'preferred': ['Google US English',
                             'Microsoft Zira - English (United States)',
                             'Alex', 'Samantha'],
                'description': 'American English with natural intonation'
            }
        }
        return jsonify({
            "voice_recommendations": voice_recommendations,
            "tips": [
                "Local/native voices provide the most natural speech",
                "Google voices generally offer excellent quality",
                "Slower speech rates improve comprehension",
                "Proper text cleaning enhances naturalness"
            ],
            "message": "Optimized for natural, native-like speech (English only)"
        })
    except Exception as e:  # Broad exception needed for error handling
        logger.error("Error getting voice information: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route('/voice/elevenlabs/status', methods=['GET'])
def elevenlabs_status():
    """Check ElevenLabs configuration status."""
    try:
        if not ELEVENLABS_AVAILABLE:
            return jsonify({
                "available": False,
                "error": "ElevenLabs library not installed. Run: pip install elevenlabs"
            })

        if not os.getenv('ELEVENLABS_API_KEY'):
            return jsonify({
                "available": False,
                "error": "ELEVENLABS_API_KEY not configured in environment variables"
            })

        # Test API connection by getting voice info
        try:
            all_voices = voices()
            current_voice_info = None

            for voice in all_voices:
                if voice.voice_id == ELEVENLABS_VOICE_ID:
                    current_voice_info = {
                        "voice_id": voice.voice_id,
                        "name": voice.name,
                        "category": voice.category
                    }
                    break

            return jsonify({
                "available": True,
                "configured_voice_id": ELEVENLABS_VOICE_ID,
                "voice_info": current_voice_info,
                "total_voices": len(all_voices),
                "status": "ElevenLabs ready for high-quality English TTS"
            })

        except Exception as api_error:  # Broad exception needed for API errors
            return jsonify({
                "available": False,
                "error": f"ElevenLabs API error: {str(api_error)}"
            })

    except Exception as e:  # Broad exception needed for error handling
        logger.error("Error checking ElevenLabs status: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route('/voice/elevenlabs/voices', methods=['GET'])
def get_elevenlabs_voices():
    """Get available ElevenLabs voices."""
    try:
        if not ELEVENLABS_AVAILABLE:
            return jsonify({"error": "ElevenLabs not available"}), 503

        if not os.getenv('ELEVENLABS_API_KEY'):
            return jsonify({"error": "ElevenLabs API key not configured"}), 503

        all_voices = voices()

        voice_list = []
        for voice in all_voices:
            voice_list.append({
                "voice_id": voice.voice_id,
                "name": voice.name,
                "category": voice.category,
                # Mark as current if matches any active voice (default, Rick, or Kurzgesagt)
                "is_current": voice.voice_id in [ELEVENLABS_VOICE_ID,
                                               RICK_VOICE_ID, KURZGESAGT_VOICE_ID]
            })

        return jsonify({
            "voices": voice_list,
            "current_voice_id": ELEVENLABS_VOICE_ID,
            "total_count": len(voice_list)
        })

    except Exception as e:  # Broad exception needed for error handling
        logger.error("Error getting ElevenLabs voices: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route('/rick/tts', methods=['POST'])
def rick_tts():
    """Generate Rick Sanchez style TTS using ElevenLabs with custom voice settings."""
    try:
        if not ELEVENLABS_AVAILABLE:
            return jsonify({"error": "ElevenLabs not available"}), 503

        if not ELEVENLABS_API_KEY:
            return jsonify({"error": "ElevenLabs API key not configured"}), 503

        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        text = data.get('text', '').strip()
        if not text:
            return jsonify({"error": "Text is required"}), 400

        # Clean text for Rick-style speech (add some Rick-isms if not present)
        rick_text = clean_text_for_rick_speech(text)

        # Use the custom Rick voice ID or fallback to default
        voice_id = RICK_VOICE_ID

        # Make request to ElevenLabs API with Rick-optimized settings
        response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "text": rick_text,
                "voice_settings": {
                    "stability": 0.45,           # More expressive for Rick's manic style
                    "similarity_boost": 0.85,    # Keep it sounding like Rick
                    "style": 0.8,               # Add more personality
                    "use_speaker_boost": True    # Enhance voice clarity
                }
            },
            timeout=10  # Set a timeout for the request
        )

        if response.status_code != 200:
            logger.error("ElevenLabs API error: %s - %s", response.status_code, response.text)
            return jsonify({"error": "Failed to generate Rick TTS audio"}), 500

        # Return audio as base64 for easier handling
        audio_base64 = base64.b64encode(response.content).decode('utf-8')

        return jsonify({
            "text": rick_text,
            "original_text": text,
            "audio_base64": audio_base64,
            "audio_format": "mp3",
            "provider": "elevenlabs_rick",
            "voice_id": voice_id,
            "message": "Rick Sanchez style TTS generated successfully!"
        })

    except Exception as e:  # Broad exception needed for error handling
        logger.error("Error in Rick TTS: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route('/rick/tts/file', methods=['POST'])
def rick_tts_file():
    """Generate Rick Sanchez style TTS and return as audio file."""
    try:
        if not ELEVENLABS_AVAILABLE:
            return jsonify({"error": "ElevenLabs not available"}), 503

        if not ELEVENLABS_API_KEY:
            return jsonify({"error": "ElevenLabs API key not configured"}), 503

        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        text = data.get('text', '').strip()
        if not text:
            return jsonify({"error": "Text is required"}), 400

        # Clean text for Rick-style speech
        rick_text = clean_text_for_rick_speech(text)

        # Use the custom Rick voice ID or fallback to default
        voice_id = RICK_VOICE_ID

        # Make request to ElevenLabs API
        response = requests.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "text": rick_text,
                "voice_settings": {
                    "stability": 0.45,           # More expressive
                    "similarity_boost": 0.85,    # More like Rick
                    "style": 0.8,               # Add personality
                    "use_speaker_boost": True
                }
            },
            timeout=10  # Set a timeout for the request
        )

        if response.status_code != 200:
            logger.error("ElevenLabs API error: %s - %s", response.status_code, response.text)
            return jsonify({"error": "Failed to generate Rick TTS audio"}), 500

        # Save audio to temporary file
        with NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
            temp_audio.write(response.content)
            temp_audio.flush()
            temp_audio.close()
            return send_file(
                temp_audio.name,
                mimetype="audio/mpeg",
                as_attachment=True,
                download_name=f"rick_tts_{uuid.uuid4().hex[:8]}.mp3"
            )

    except Exception as e:  # Broad exception needed for error handling
        logger.error("Error in Rick TTS file: %s", e)
        return jsonify({"error": str(e)}), 500

def clean_text_for_rick_speech(text):
    """Clean and enhance text for Rick Sanchez style speech."""

    rick_text = text

    # Remove markdown formatting
    rick_text = re.sub(r'\*\*(.*?)\*\*', r'\1', rick_text)
    rick_text = re.sub(r'\*(.*?)\*', r'\1', rick_text)
    rick_text = re.sub(r'`(.*?)`', r'\1', rick_text)

    # Add Rick-style speech patterns (but don't overdo it)
    rick_text = rick_text.replace('very', 'very very')
    rick_text = rick_text.replace('really', 'really really')

    # Clean up spacing
    rick_text = re.sub(r'\s+', ' ', rick_text).strip()

    # Add some Rick-style interjections occasionally (sparingly)
    if len(rick_text) > 100 and 'you know' not in rick_text.lower():
        sentences = rick_text.split('.')
        if len(sentences) > 2:
            # Insert a casual interjection in the middle
            mid_point = len(sentences) // 2
            sentences[mid_point] = sentences[mid_point] + ', you know'
            rick_text = '.'.join(sentences)

    return rick_text

@app.route('/rick/tts/status', methods=['GET'])
def rick_tts_status():
    """Check Rick TTS configuration and voice status."""
    try:
        if not ELEVENLABS_AVAILABLE:
            return jsonify({
                "available": False,
                "error": "ElevenLabs library not installed. Run: pip install elevenlabs"
            })

        if not ELEVENLABS_API_KEY:
            return jsonify({
                "available": False,
                "error": "ELEVENLABS_API_KEY not configured in environment variables"
            })

        # Check if custom Rick voice is configured
        rick_voice_configured = RICK_VOICE_ID != ELEVENLABS_VOICE_ID

        # Test API connection and get voice info
        try:
            all_voices = voices()
            rick_voice_info = None

            for voice in all_voices:
                if voice.voice_id == RICK_VOICE_ID:
                    rick_voice_info = {
                        "voice_id": voice.voice_id,
                        "name": voice.name,
                        "category": voice.category
                    }
                    break

            status_text = ("Rick TTS ready!" if rick_voice_info
                          else "Rick voice ID not found in available voices")

            return jsonify({
                "available": True,
                "rick_voice_configured": rick_voice_configured,
                "rick_voice_id": RICK_VOICE_ID,
                "voice_info": rick_voice_info,
                "endpoints": {
                    "json": "/rick/tts",
                    "file": "/rick/tts/file"
                },
                "voice_settings": {
                    "stability": 0.45,
                    "similarity_boost": 0.85,
                    "style": 0.8,
                    "use_speaker_boost": True
                },
                "status": status_text
            })

        except Exception as api_error:  # Broad exception needed for API errors
            return jsonify({
                "available": False,
                "error": f"ElevenLabs API error: {str(api_error)}"
            })

    except Exception as e:  # Broad exception needed for error handling
        logger.error("Error checking Rick TTS status: %s", e)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Check if RAG agent is available
    if not RAG_AGENT:
        logger.warning("⚠️ Starting server without RAG agent - check your configuration!")
    else:
        # Check index stats
        try:
            stats = RAG_AGENT.index.describe_index_stats()
            logger.info("📊 Knowledge base ready: %s vectors", stats.total_vector_count)

            if stats.total_vector_count == 0:
                logger.warning("⚠️ Knowledge base is empty - run data upload first!")
        except Exception as e:  # Broad exception needed for error handling
            logger.error("❌ Error checking knowledge base: %s", e)

    # Start the Flask development server
    logger.info("🚀 Starting Kurzgesagt RAG Web Interface...")
    logger.info("🌐 Open your browser to: http://localhost:5000")

    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        threaded=True
    )
