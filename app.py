from flask import Flask, request, jsonify
from code.kurzgesagt_rag_agent import KurzgesagtRAGAgent

app = Flask(__name__)
rag_agent = KurzgesagtRAGAgent()

@app.route('/ask', methods=['POST'])
def ask_question():
    data = request.get_json()
    question = data.get('question', '')

    if not question:
        return jsonify({"error": "Question is required"}), 400

    try:
        answer_data, matches, language = rag_agent.generate_answer(question)
        return jsonify({
            "answer": answer_data.get('answer'),
            "confidence": answer_data.get('confidence'),
            "sources": answer_data.get('sources'),
            "language": answer_data.get('language')
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
