"""
Kurzgesagt RAG Agent with LangChain
Retrieves relevant information and generates comprehensive answers
"""

import os
from dotenv import load_dotenv
from openai import OpenAI
import pinecone
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain.chains import SequentialChain
import json
from context_retriever import retrieve_context, format_context
from language_utils import detect_language_and_translate

class KurzgesagtRAGAgent:
    def __init__(self):
        load_dotenv()
        
        # Initialize clients
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.index = pc.Index("kurzgesagt-transcripts")
        
        # Initialize LangChain LLM
        self.llm = ChatOpenAI(
            model="gpt-4",  # Use GPT-4 for better reasoning
            temperature=0.7,  # Balanced creativity/accuracy
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Create output parser for structured responses
        self.response_schemas = [
            ResponseSchema(name="answer", description="The main answer to the question in the specified language"),
            ResponseSchema(name="confidence", description="Confidence level (high/medium/low) based on available context"),
            ResponseSchema(name="sources_used", description="Number of sources used to generate the answer"),
            ResponseSchema(name="language", description="The language of the response")
        ]
        
        self.output_parser = StructuredOutputParser.from_response_schemas(self.response_schemas)
        format_instructions = self.output_parser.get_format_instructions()
        
        # Create RAG prompt template for multilingual support with structured output
        self.rag_prompt = PromptTemplate(
            input_variables=["question", "context", "target_language"],
            template="""You are a knowledgeable science communicator inspired by Kurzgesagt's style. 
Your task is to answer questions using the provided context from Kurzgesagt videos.

Guidelines:
- Use ONLY the provided context to answer the question. Do not use external knowledge.
- If the context doesn't contain enough information, say so clearly and return 'I can't answer that based on the available context.'
- Always respond in the specified target language
- Use simple language and analogies to explain complex concepts
- Reference the relevant video titles explicitly in your answer
- Be enthusiastic about science while remaining accurate
- IMPORTANT: Answer in {target_language}. If the question is not in English, translate your response to match the language of the question.

Context from Kurzgesagt videos:
{context}

Question: {question}

{format_instructions}

Provide your response in the specified JSON format:""",
            partial_variables={"format_instructions": format_instructions}
        )
        
        # Create LangChain chain
        self.rag_chain = LLMChain(
            llm=self.llm,
            prompt=self.rag_prompt,
            verbose=False
        )
        
        # Initialize in-memory cache for short-term memory
        self.cache = {}

        print("🧠 Kurzgesagt RAG Agent Ready!")
        print("=" * 40)
    
    def _get_from_cache(self, key):
        """Retrieve an item from the cache."""
        return self.cache.get(key)

    def _add_to_cache(self, key, value):
        """Add an item to the cache."""
        self.cache[key] = value

    def retrieve_context(self, query, top_k=3):
        return retrieve_context(self.index, query, self.openai_client, self.cache, top_k)

    def format_context(self, matches):
        return format_context(matches)
    
    def generate_answer(self, question, max_tokens=500):
        """Generate answer using RAG with multilingual support and caching."""
        # Check cache first
        cached_result = self._get_from_cache(question)
        if cached_result:
            print("🔄 Using cached answer for question.")
            return cached_result

        try:
            print(f"🔍 Processing question: '{question}'")

            # Step 1: Detect language and translate to English for retrieval
            print("🌍 Detecting language...")
            detected_language, english_question = detect_language_and_translate(self.llm, question)
            print(f"📝 Detected language: {detected_language}")

            if detected_language.lower() != "english":
                print(f"🔄 English translation: '{english_question}'")

            # Step 2: Retrieve relevant context using English question
            print(f"🔍 Retrieving relevant information...")
            matches = self.retrieve_context(english_question, top_k=5)

            if not matches:
                no_results_msg = "I couldn't find relevant information in the Kurzgesagt transcripts to answer your question."
                if detected_language.lower() != "english":
                    no_results_msg = self.translate_to_target_language(no_results_msg, detected_language)

                # Return structured response even for no results
                structured_answer = {
                    'answer': no_results_msg,
                    'confidence': 'low',
                    'sources_used': 0,
                    'language': detected_language,
                    'sources': [],
                    'raw_response': no_results_msg
                }
                self._add_to_cache(question, (structured_answer, [], detected_language))
                return structured_answer, [], detected_language

            # Step 3: Format context and extract sources
            context = self.format_context(matches)
            sources = [match.metadata.get('video_title', 'Unknown') for match in matches]

            print(f"📚 Found {len(matches)} relevant segments")
            print(f"🧠 Generating answer in {detected_language}...")

            # Step 4: Generate answer using LLM with language specification
            raw_response = self.rag_chain.run(
                question=question,  # Use original question
                context=context,
                target_language=detected_language
            )

            # Parse the structured response
            try:
                parsed_response = self.output_parser.parse(raw_response)

                # Create a structured answer object
                structured_answer = {
                    'answer': parsed_response.get('answer', raw_response),
                    'confidence': parsed_response.get('confidence', 'medium'),
                    'sources_used': parsed_response.get('sources_used', len(matches)),
                    'language': parsed_response.get('language', detected_language),
                    'sources': sources,
                    'raw_response': raw_response  # Keep raw response for debugging
                }

                # Cache the result
                self._add_to_cache(question, (structured_answer, matches, detected_language))

                return structured_answer, matches, detected_language

            except Exception as parse_error:
                print(f"⚠️ Parser error: {parse_error}")
                print("📝 Using raw response as fallback")

                # Fallback to raw response if parsing fails
                structured_answer = {
                    'answer': raw_response,
                    'confidence': 'medium',
                    'sources_used': len(matches),
                    'language': detected_language,
                    'sources': sources,
                    'raw_response': raw_response
                }

                # Cache the result
                self._add_to_cache(question, (structured_answer, matches, detected_language))

                return structured_answer, matches, detected_language

        except Exception as e:
            print(f"❌ Generation error: {e}")
            error_msg = f"Error generating answer: {str(e)}"

            # Return structured error response
            structured_error = {
                'answer': error_msg,
                'confidence': 'low',
                'sources_used': 0,
                'language': 'English',
                'sources': [],
                'raw_response': error_msg
            }
            self._add_to_cache(question, (structured_error, [], "English"))
            return structured_error, [], "English"
    
    def display_answer_with_sources(self, question, answer_data, matches, language="English"):
        """Display answer with source information - handles both structured and simple answers"""
        print(f"\n❓ Question: {question}")
        if language.lower() != "english":
            print(f"🌍 Language: {language}")
        print("=" * 60)

        # Handle structured answer
        if isinstance(answer_data, dict):
            answer = answer_data.get('answer', str(answer_data))
            confidence = answer_data.get('confidence', 'medium')
            sources_used = answer_data.get('sources_used', len(matches))
            answer_language = answer_data.get('language', language)
            sources = answer_data.get('sources', [])

            print(f"\n🤖 Answer:")
            print(answer)
            print(f"\n📊 Confidence: {confidence.upper()}")
            print(f"📚 Sources used: {sources_used}")

            # List the titles of the sources used
            if sources:
                print("\n📋 Source Titles:")
                for i, source in enumerate(sources, 1):
                    print(f"   {i}. {source}")

            if answer_language.lower() != language.lower():
                print(f"🌍 Response language: {answer_language}")
        else:
            # Handle simple string answer (fallback)
            print(f"\n🤖 Answer:")
            print(answer_data)

        print(f"\n📚 Sources ({len(matches)} relevant segments):")
        print("-" * 40)

        for i, match in enumerate(matches, 1):
            video_title = match.metadata.get('video_title', 'Unknown')
            score = match.score
            source_file = match.metadata.get('source', 'Unknown')

            print(f"{i}. 📹 {video_title}")
            print(f"   🎯 Relevance: {score:.3f}")
            print(f"   📄 File: {source_file}")
    
    def get_clean_answer(self, answer_data):
        """Extract just the answer text for API/UI integration"""
        if isinstance(answer_data, dict):
            return answer_data.get('answer', str(answer_data))
        return str(answer_data)
    

def main():
    """Main function"""
    print("🧬 Kurzgesagt Multilingual RAG Agent")
    print("Retrieval-Augmented Generation for Science Questions")
    print("🌍 Ask questions in any language - get answers in the same language!")
    print("=" * 65)

    try:
        # Initialize RAG agent
        rag_agent = KurzgesagtRAGAgent()

        # Check index stats
        stats = rag_agent.index.describe_index_stats()
        print(f"📊 Knowledge base: {stats.total_vector_count} vector chunks")

        if stats.total_vector_count == 0:
            print("❌ Index is empty! Run openai_pinecone_uploader.py first")
            return

        print("\nChoose an option:")
        print("1. Quick multilingual demo")
        print("2. Interactive multilingual chat")
        print("3. Single question mode (any language)")
        print("4. Exit")

        choice = input("\nEnter choice (1-4): ").strip()

        if choice == "1":
            from interactive_modes import quick_demo
            quick_demo(rag_agent)
        elif choice == "2":
            from interactive_modes import interactive_rag_chat
            interactive_rag_chat(rag_agent)
        elif choice == "3":
            question = input("Enter your question (any language): ").strip()
            if question:
                result = rag_agent.generate_answer(question)
                if isinstance(result, tuple) and len(result) >= 3:
                    answer_data, matches, language = result
                    rag_agent.display_answer_with_sources(question, answer_data, matches, language)
                elif isinstance(result, tuple):
                    answer_data, matches = result
                    rag_agent.display_answer_with_sources(question, answer_data, matches)
                else:
                    print(f"\n🤖 Answer: {result}")
        elif choice == "4":
            print("👋 Goodbye!")
        else:
            print("❌ Invalid choice")

    except Exception as e:
        print(f"❌ Error: {e}")
        print("Make sure you have:")
        print("1. Uploaded data to Pinecone (run openai_pinecone_uploader.py)")
        print("2. Set OPENAI_API_KEY and PINECONE_API_KEY in .env")
        print("3. Installed required packages: pip install langchain")

if __name__ == "__main__":
    main()
