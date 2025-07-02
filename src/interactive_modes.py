"""
Interactive Modes Module
Handles interactive and demo modes for the Kurzgesagt RAG Agent.
"""

def interactive_rag_chat(rag_agent):
    """Interactive RAG chat interface with multilingual support."""
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
        if question.lower() == 'examples':
            show_multilingual_examples()
            continue
        if not question:
            continue
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
    """Show example questions in multiple languages."""
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
    """Quick demonstration of multilingual RAG capabilities."""
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

def rick_sanchez_chat(rag_agent):
    """Interactive chat with Rick Sanchez personality."""
    print("\n🧪 *BURP* Rick Sanchez Science Chat Mode")
    print("Wubba lubba dub dub! I'm Rick Sanchez, the smartest scientist in the universe!")
    print("Ask me any science question and I'll explain it like you're Morty (aka an idiot)")
    print("Type 'quit' to exit, 'wubba' for Rick quotes")
    print("-" * 70)
    rick_quotes = [
        "*burp* Science, Morty! It's like a... a universal language, except everyone's stupid.",
        "Listen Morty, the universe is basically an animal. It grazes on the ordinary.",
        "*burp* Nobody exists on purpose, nobody belongs anywhere, everybody's gonna die. Come watch TV?",
        "I'm not looking for judgment, just a yes or no - can you assimilate a giraffe?",
        "Morty, I need you to *burp* put these seeds way up inside your butthole.",
        "Existence is pain, Morty! We're all just trying to find our way in this crazy universe!"
    ]
    session_id = "rick_dimension_c137"
    quote_index = 0
    while True:
        question = input("\n🧪 What do you want to know, Morty? ").strip()
        if question.lower() == 'quit':
            print("🧪 Peace out, Morty! *burp* Don't get eaten by interdimensional beings!")
            break
        if question.lower() == 'wubba':
            print(f"🧪 Rick says: {rick_quotes[quote_index % len(rick_quotes)]}")
            quote_index += 1
            continue
        if not question:
            print("🧪 *burp* Come on Morty, ask me something! Don't waste my time!")
            continue
        result = rag_agent.generate_answer(question, session_id, mode="crazy_scientist")
        if isinstance(result, tuple) and len(result) >= 3:
            answer_data, matches, language = result
            rag_agent.display_answer_with_sources(question, answer_data, matches, language)
        elif isinstance(result, tuple):
            answer_data, matches = result
            rag_agent.display_answer_with_sources(question, answer_data, matches)
        else:
            print(f"\n🧪 Rick says: {result}")

def crazy_scientist_demo(rag_agent):
    """Demo of Rick Sanchez mode with science questions."""
    demo_questions = [
        "How does the immune system work?",
        "What happens inside a black hole?",
        "Why should we worry about climate change?"
    ]
    print("\n🧪 *BURP* Rick Sanchez Science Demo")
    print("Wubba lubba dub dub! Watch me explain science like a genius!")
    print("=" * 50)
    session_id = "rick_demo_session"
    for question in demo_questions:
        print(f"\n{'='*70}")
        print(f"🧪 Rick tackles: {question}")
        result = rag_agent.generate_answer(question, session_id, mode="crazy_scientist")
        if isinstance(result, tuple) and len(result) >= 3:
            answer, matches, detected_lang = result
            rag_agent.display_answer_with_sources(question, answer, matches, detected_lang)
        elif isinstance(result, tuple):
            answer, matches = result
            rag_agent.display_answer_with_sources(question, answer, matches)
        else:
            print(f"\n🧪 Rick says: {result}")
        input("\n*burp* Press Enter for the next question, Morty...")
    print("\n🧪 That's how you do science, Morty! *burp* Wubba lubba dub dub!")
