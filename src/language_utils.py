"""
Language Utilities Module
Handles language detection and translation for the Kurzgesagt RAG Agent.
"""

def detect_language_and_translate(llm, text):
    """Detect the language of the input text and translate it to English."""
    try:
        # Detect language using LangChain's ChatOpenAI client
        detection_prompt = f"""
        Analyze this text and determine:
        1. What language is it in? (respond with language name in English)
        2. If it's not in English, provide an English translation
        3. If it's already in English, just say "English" and repeat the text

        Text: "{text}"

        Respond in this format:
        Language: [detected language]
        Translation: [English version of the text]
        """

        response = llm.invoke(detection_prompt)
        response_text = response.content

        # Parse the response
        lines = response_text.strip().split('\n')
        language = "English"
        english_text = text

        for line in lines:
            if line.startswith("Language:"):
                language = line.replace("Language:", "").strip()
            elif line.startswith("Translation:"):
                english_text = line.replace("Translation:", "").strip()

        return language, english_text

    except Exception as e:
        print(f"❌ Language detection/translation error: {e}")
        return "unknown", text
