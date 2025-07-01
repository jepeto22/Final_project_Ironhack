from flask import Flask, request, jsonify, session, render_template
from src.kurzgesagt_rag_agent import KurzgesagtRAGAgent
from src.interactive_modes import quick_demo, interactive_rag_chat, show_multilingual_examples
import uuid
import os
import logging
import io
import sys
from contextlib import redirect_stdout

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'kurzgesagt-rag-secret-key-2025')

# Initialize RAG agent with error handling
try:
    rag_agent = KurzgesagtRAGAgent()
    logger.info("✅ Kurzgesagt RAG Agent initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize RAG Agent: {e}")
    rag_agent = None

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
        "agent_available": rag_agent is not None,
        "version": "1.0.0"
    })

@app.route('/ask', methods=['POST'])
def ask_question():
    """Process user questions and return AI responses."""
    if not rag_agent:
        return jsonify({
            "error": "RAG Agent not available. Please check server configuration."
        }), 503

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        question = data.get('question', '').strip()
        session_id = data.get('session_id') or get_session_id()

        if not question:
            return jsonify({"error": "Question is required"}), 400

        logger.info(f"Processing question from session {session_id[:8]}...")

        # Generate answer using RAG agent
        result = rag_agent.generate_answer(question, session_id)
        
        if isinstance(result, tuple) and len(result) >= 3:
            answer_data, matches, language = result
        else:
            return jsonify({"error": "Invalid response format from RAG agent"}), 500

        # Extract structured response
        if isinstance(answer_data, dict):
            response = {
                "answer": answer_data.get('answer', 'No answer available'),
                "confidence": answer_data.get('confidence', 'medium'),
                "sources": answer_data.get('sources', []),
                "sources_used": answer_data.get('sources_used', len(matches)),
                "language": answer_data.get('language', language),
                "session_id": session_id,
                "is_follow_up": answer_data.get('is_follow_up', False)
            }
        else:
            # Fallback for simple string responses
            response = {
                "answer": str(answer_data),
                "confidence": "medium",
                "sources": [match.metadata.get('video_title', 'Unknown') for match in matches],
                "sources_used": len(matches),
                "language": language,
                "session_id": session_id,
                "is_follow_up": False
            }

        logger.info(f"Successfully processed question with confidence: {response['confidence']}")
        return jsonify(response)

    except Exception as e:
        logger.error(f"Error processing question: {e}")
        return jsonify({
            "error": f"An error occurred while processing your question: {str(e)}"
        }), 500

@app.route('/conversation/context', methods=['GET'])
def get_conversation_context():
    """Get current conversation context for a session."""
    if not rag_agent:
        return jsonify({"error": "RAG Agent not available"}), 503

    try:
        session_id = request.args.get('session_id') or get_session_id()
        context = rag_agent.get_conversation_context(session_id)
        
        return jsonify({
            "session_id": session_id,
            "context": context
        })
    except Exception as e:
        logger.error(f"Error getting conversation context: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/conversation/clear', methods=['POST'])
def clear_conversation():
    """Clear conversation history for a session."""
    if not rag_agent:
        return jsonify({"error": "RAG Agent not available"}), 503

    try:
        data = request.get_json()
        session_id = data.get('session_id') if data else get_session_id()
        
        rag_agent.clear_conversation(session_id)
        
        return jsonify({
            "message": "Conversation cleared successfully",
            "session_id": session_id
        })
    except Exception as e:
        logger.error(f"Error clearing conversation: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/stats')
def get_stats():
    """Get system statistics."""
    if not rag_agent:
        return jsonify({"error": "RAG Agent not available"}), 503

    try:
        # Get memory stats
        memory_stats = rag_agent.get_memory_stats()
        
        # Get index stats
        index_stats = rag_agent.index.describe_index_stats()
        
        return jsonify({
            "memory_stats": memory_stats,
            "knowledge_base": {
                "total_vectors": index_stats.total_vector_count,
                "dimension": index_stats.dimension
            },
            "agent_status": "online"
        })
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/modes')
def get_available_modes():
    """Get available interactive modes."""
    return jsonify({
        "modes": [
            {
                "id": 1,
                "name": "Quick multilingual demo",
                "description": "Demonstrate RAG capabilities with pre-defined multilingual questions",
                "endpoint": "/demo"
            },
            {
                "id": 2,
                "name": "Interactive multilingual chat",
                "description": "Start a conversation in any language with follow-up support",
                "endpoint": "/chat"
            },
            {
                "id": 3,
                "name": "Single question mode",
                "description": "Ask a single question in any language",
                "endpoint": "/ask"
            },
            {
                "id": 4,
                "name": "Get examples",
                "description": "View example questions in multiple languages",
                "endpoint": "/examples"
            }
        ]
    })

@app.route('/demo', methods=['POST'])
def run_demo():
    """Run the quick multilingual demo."""
    if not rag_agent:
        return jsonify({"error": "RAG Agent not available"}), 503

    try:
        # Capture the demo output
        demo_questions = [
            ("English", "How does the immune system fight infections?"),
            ("Spanish", "¿Qué pasa dentro de un agujero negro?"),
            ("French", "Pourquoi devrions-nous nous inquiéter de la guerre nucléaire?")
        ]

        demo_results = []
        session_id = str(uuid.uuid4())

        for lang, question in demo_questions:
            result = rag_agent.generate_answer(question, session_id)
            
            if isinstance(result, tuple) and len(result) >= 3:
                answer_data, matches, detected_lang = result
            else:
                answer_data, matches, detected_lang = result, [], lang

            demo_results.append({
                "language": lang,
                "question": question,
                "answer": answer_data.get('answer', str(answer_data)) if isinstance(answer_data, dict) else str(answer_data),
                "detected_language": detected_lang,
                "confidence": answer_data.get('confidence', 'medium') if isinstance(answer_data, dict) else 'medium',
                "sources": [match.metadata.get('video_title', 'Unknown') for match in matches] if matches else [],
                "sources_used": len(matches) if matches else 0
            })

        return jsonify({
            "demo_results": demo_results,
            "session_id": session_id,
            "message": "Demo completed successfully"
        })

    except Exception as e:
        logger.error(f"Error running demo: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/chat/start', methods=['POST'])
def start_chat():
    """Start an interactive chat session."""
    if not rag_agent:
        return jsonify({"error": "RAG Agent not available"}), 503

    try:
        session_id = str(uuid.uuid4())
        
        return jsonify({
            "session_id": session_id,
            "message": "Interactive chat session started",
            "instructions": {
                "description": "Ask questions in any language - answers will be in the same language!",
                "supported_languages": ["English", "Spanish", "French", "German", "Italian", "Portuguese", "etc."],
                "commands": {
                    "examples": "Type 'examples' to see sample questions",
                    "quit": "Type 'quit' to end the session"
                }
            }
        })

    except Exception as e:
        logger.error(f"Error starting chat: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/chat/message', methods=['POST'])
def chat_message():
    """Send a message in the chat session."""
    if not rag_agent:
        return jsonify({"error": "RAG Agent not available"}), 503

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No JSON data provided"}), 400

        message = data.get('message', '').strip()
        session_id = data.get('session_id', str(uuid.uuid4()))

        if not message:
            return jsonify({"error": "Message is required"}), 400

        # Handle special commands
        if message.lower() == 'examples':
            examples = get_multilingual_examples()
            return jsonify({
                "type": "examples",
                "examples": examples,
                "session_id": session_id
            })

        if message.lower() in ['quit', 'exit', 'q']:
            return jsonify({
                "type": "quit",
                "message": "Thanks for exploring science with Kurzgesagt RAG!",
                "session_id": session_id
            })

        # Process the question
        result = rag_agent.generate_answer(message, session_id)
        
        if isinstance(result, tuple) and len(result) >= 3:
            answer_data, matches, language = result
        else:
            return jsonify({"error": "Invalid response format from RAG agent"}), 500

        # Extract structured response
        if isinstance(answer_data, dict):
            response = {
                "type": "answer",
                "question": message,
                "answer": answer_data.get('answer', 'No answer available'),
                "confidence": answer_data.get('confidence', 'medium'),
                "sources": answer_data.get('sources', []),
                "sources_used": answer_data.get('sources_used', len(matches)),
                "language": answer_data.get('language', language),
                "session_id": session_id,
                "is_follow_up": answer_data.get('is_follow_up', False)
            }
        else:
            # Fallback for simple string responses
            response = {
                "type": "answer",
                "question": message,
                "answer": str(answer_data),
                "confidence": "medium",
                "sources": [match.metadata.get('video_title', 'Unknown') for match in matches],
                "sources_used": len(matches),
                "language": language,
                "session_id": session_id,
                "is_follow_up": False
            }

        return jsonify(response)

    except Exception as e:
        logger.error(f"Error processing chat message: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/examples')
def get_examples():
    """Get multilingual example questions."""
    examples = get_multilingual_examples()
    return jsonify({
        "examples": examples,
        "instructions": "You can ask questions in any language you're comfortable with! The system will detect your language and respond accordingly."
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
        {"language": "Spanish", "question": "¿Qué pasaría si la Tierra se convirtiera en un planeta errante?"},
        {"language": "French", "question": "Que se passe-t-il dans un trou noir?"},
        {"language": "German", "question": "Was passiert in einem schwarzen Loch?"},
        {"language": "English", "question": "Why should we worry about nuclear war?"},
        {"language": "Spanish", "question": "¿Por qué deberíamos preocuparnos por la guerra nuclear?"}
    ]
@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    # Check if RAG agent is available
    if not rag_agent:
        logger.warning("⚠️ Starting server without RAG agent - check your configuration!")
    else:
        # Check index stats
        try:
            stats = rag_agent.index.describe_index_stats()
            logger.info(f"📊 Knowledge base ready: {stats.total_vector_count} vectors")
            
            if stats.total_vector_count == 0:
                logger.warning("⚠️ Knowledge base is empty - run data upload first!")
        except Exception as e:
            logger.error(f"❌ Error checking knowledge base: {e}")

    # Start the Flask development server
    logger.info("🚀 Starting Kurzgesagt RAG Web Interface...")
    logger.info("🌐 Open your browser to: http://localhost:5000")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        threaded=True
    )
