"""
Interactive Modes Module
Handles interactive and demo modes for the Kurzgesagt RAG Agent.
"""

def interactive_rag_chat(rag_agent):
    """Interactive RAG chat interface with multilingual support"""
    print("\n💬 Interactive Multilingual RAG Chat Mode")
    print("Ask questions in any language - answers will be in the same language!")
    print("Supported: English, Spanish, French, German, Italian, Portuguese, etc.")
    print("Type 'quit' to exit, 'examples' for sample questions")
    print("-" * 70)

    while True:
        question = input("\n❓ What would you like to know? (any language): ").strip()

        if question.lower() == 'quit':
            print("👋 Thanks for exploring science with Kurzgesagt RAG!")
            break
        elif question.lower() == 'examples':
            show_multilingual_examples()
            continue
        elif not question:
            continue

        # Generate RAG answer
        result = rag_agent.generate_answer(question)
        if isinstance(result, tuple) and len(result) >= 3:
            answer_data, matches, language = result
            rag_agent.display_answer_with_sources(question, answer_data, matches, language)
        elif isinstance(result, tuple):
            answer_data, matches = result
            rag_agent.display_answer_with_sources(question, answer_data, matches)
        else:
            print(f"\n🤖 Answer: {result}")

def show_multilingual_examples():
    """Show example questions in multiple languages"""
    examples = [
        ("English", "How does the immune system protect us from diseases?"),
        ("Spanish", "¿Cómo funciona el sistema inmunológico?"),
        ("French", "Comment fonctionne le système immunitaire?"),
        ("German", "Wie funktioniert das Immunsystem?"),
        ("Italian", "Come funziona il sistema immunitario?"),
        ("Portuguese", "Como funciona o sistema imunológico?"),
        ("English", "What happens inside a black hole?"),
        ("Spanish", "¿Qué pasaría si la Tierra se convirtiera en un planeta errante?"),
        ("French", "Que se passe-t-il dans un trou noir?"),
        ("German", "Was passiert in einem schwarzen Loch?"),
        ("English", "Why should we worry about nuclear war?"),
        ("Spanish", "¿Por qué deberíamos preocuparnos por la guerra nuclear?")
    ]

    print("\n💡 Example Questions (Multiple Languages):")
    for i, (lang, example) in enumerate(examples, 1):
        print(f"   {i}. [{lang}] {example}")

    print("\n🌍 You can ask questions in any language you're comfortable with!")
    print("   The system will detect your language and respond accordingly.")

def quick_demo(rag_agent):
    """Quick demonstration of multilingual RAG capabilities"""
    demo_questions = [
        ("English", "How does the immune system fight infections?"),
        ("Spanish", "¿Qué pasa dentro de un agujero negro?"),
        ("French", "Pourquoi devrions-nous nous inquiéter de la guerre nucléaire?")
    ]

    print("\n🚀 Quick Multilingual RAG Demo")
    print("=" * 40)

    for lang, question in demo_questions:
        print(f"\n{'='*70}")
        print(f"🌍 Testing with {lang} question...")
        result = rag_agent.generate_answer(question)
        if isinstance(result, tuple) and len(result) >= 3:
            answer, matches, detected_lang = result
            rag_agent.display_answer_with_sources(question, answer, matches, detected_lang)
        elif isinstance(result, tuple):
            answer, matches = result
            rag_agent.display_answer_with_sources(question, answer, matches)
        else:
            print(f"\n🤖 Answer: {result}")

        input("\nPress Enter to continue to next question...")

    print("\n🎉 Demo completed! The system can handle questions in multiple languages!")
    print("🌍 Try asking questions in your preferred language!")
