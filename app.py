from flask import Flask, request, jsonify, session
from code.kurzgesagt_rag_agent import KurzgesagtRAGAgent
import uuid
import os

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'kurzgesagt-rag-secret-key-2025')
rag_agent = KurzgesagtRAGAgent()

def get_session_id():
    """Get or create session ID for conversation tracking."""
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return session['session_id']

@app.route('/ask', methods=['POST'])
def ask_question():
    data = request.get_json()
    question = data.get('question', '')
    session_id = data.get('session_id') or get_session_id()

    if not question:
        return jsonify({"error": "Question is required"}), 400

    try:
        answer_data, matches, language = rag_agent.generate_answer(question, session_id)
        
        response = {
            "answer": answer_data.get('answer'),
            "confidence": answer_data.get('confidence'),
            "sources": answer_data.get('sources'),
            "language": answer_data.get('language'),
            "session_id": session_id,
            "is_follow_up": answer_data.get('is_follow_up', False)
        }
        
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/conversation/context', methods=['GET'])
def get_conversation_context():
    """Get current conversation context."""
    session_id = request.args.get('session_id') or get_session_id()
    
    try:
        context = rag_agent.get_conversation_context(session_id)
        return jsonify({
            "session_id": session_id,
            "context": context
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/conversation/clear', methods=['POST'])
def clear_conversation():
    """Clear conversation memory for a session."""
    data = request.get_json() or {}
    session_id = data.get('session_id') or get_session_id()
    
    try:
        rag_agent.clear_conversation(session_id)
        return jsonify({
            "message": "Conversation cleared successfully",
            "session_id": session_id
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/stats', methods=['GET'])
def get_stats():
    """Get system statistics."""
    try:
        memory_stats = rag_agent.get_memory_stats()
        cache_stats = rag_agent.semantic_cache.get_stats()
        
        return jsonify({
            "conversation_memory": memory_stats,
            "semantic_cache": cache_stats
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "features": {
            "semantic_caching": True,
            "conversation_memory": True,
            "multilingual_support": True
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
