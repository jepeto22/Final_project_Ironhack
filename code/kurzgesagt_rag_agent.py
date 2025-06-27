"""
Kurzgesagt RAG Agent with LangChain
Retrieves relevant information and generates comprehensive answers
"""

import os
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from context_retriever import retrieve_context, format_context
from language_utils import detect_language_and_translate
from semantic_cache import SemanticCache
from simple_conversation_memory import SimpleConversationMemory

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
        
        # Initialize semantic cache for intelligent similarity matching
        self.semantic_cache = SemanticCache(similarity_threshold=0.85)
        
        # Initialize simple conversation memory for follow-up questions (last 4 Q&A pairs)
        self.conversation_memory = SimpleConversationMemory(max_history=4)

        print("🧠 Kurzgesagt RAG Agent Ready!")
        print("🎯 Semantic caching enabled (similarity threshold: 85%)")
        print("💭 Simple conversation memory enabled (last 4 Q&A pairs)")
        print("=" * 40)
    
    def _get_embedding(self, query):
        """Generate embedding for a query."""
        try:
            query_response = self.openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=[query]
            )
            return query_response.data[0].embedding
        except Exception as e:
            print(f"❌ Embedding error: {e}")
            return None

    def _get_from_cache(self, query):
        """Retrieve from semantic cache with similarity matching."""
        # Check for exact match first
        exact_match = self.semantic_cache.get_exact(query)
        if exact_match:
            print("🎯 EXACT cache hit!")
            return exact_match['results']
        
        # Check for semantic similarity
        query_embedding = self._get_embedding(query)
        if query_embedding:
            similar_match = self.semantic_cache.find_similar(query_embedding)
            if similar_match:
                cached_query, results, similarity = similar_match
                print(f"🔄 SEMANTIC cache hit (similarity: {similarity:.3f})")
                print(f"   Similar to: '{cached_query[:50]}...'")
                return results
        
        return None

    def _add_to_cache(self, query, results):
        """Add to semantic cache with embedding."""
        query_embedding = self._get_embedding(query)
        if query_embedding:
            self.semantic_cache.add(query, query_embedding, results)
            print(f"💾 Added to semantic cache")

    def retrieve_context(self, query, top_k=3):
        return retrieve_context(self.index, query, self.openai_client, top_k=top_k)

    def format_context(self, matches):
        return format_context(matches)
    
    def generate_answer(self, question, session_id="default", max_tokens=500):
        """Generate answer using RAG with multilingual support, semantic caching, and simple conversation memory."""
        print(f"🔍 Processing question: '{question}'")

        # Step 1: Check if this is likely a follow-up question
        is_follow_up = self.conversation_memory.is_likely_followup(question)
        conversation_context = ""
        
        if is_follow_up:
            print(f"🔗 Detected potential follow-up question")
            # Get recent conversation context to help with the query
            conversation_context = self.conversation_memory.get_recent_context(session_id, max_pairs=2)
            if conversation_context:
                print(f"💭 Using recent conversation context")

        # Step 2: Check semantic cache first
        cached_result = self._get_from_cache(question)
        if cached_result:
            # Add to conversation memory even for cached results
            answer_data, matches, language = cached_result
            if isinstance(answer_data, dict):
                clean_answer = answer_data.get('answer', str(answer_data))
            else:
                clean_answer = str(answer_data)
            
            self.conversation_memory.add_qa_pair(question, clean_answer, session_id)
            return cached_result

        try:
            # Step 3: Detect language and translate to English for retrieval
            print("🌍 Detecting language...")
            detected_language, english_question = detect_language_and_translate(self.llm, question)
            print(f"📝 Detected language: {detected_language}")

            if detected_language.lower() != "english":
                print(f"🔄 English translation: '{english_question}'")

            # Step 4: Retrieve relevant context using English question
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
                    'raw_response': no_results_msg,
                    'is_follow_up': is_follow_up
                }
                result = (structured_answer, [], detected_language)
                
                # Add to conversation memory
                self.conversation_memory.add_qa_pair(question, no_results_msg, session_id)
                
                # Cache the result
                self._add_to_cache(question, result)
                return result

            # Step 5: Format context and extract sources
            context = self.format_context(matches)
            sources = [match.metadata.get('video_title', 'Unknown') for match in matches]

            # Add conversation context if it's a follow-up
            if is_follow_up and conversation_context:
                context = f"Recent conversation:\n{conversation_context}\n\nRelevant information:\n{context}"

            print(f"📚 Found {len(matches)} relevant segments")
            print(f"🧠 Generating answer in {detected_language}...")

            # Step 6: Generate answer using LLM with language specification
            raw_response = self.rag_chain.run(
                question=question,
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
                    'raw_response': raw_response,
                    'is_follow_up': is_follow_up
                }

                # Cache the result
                result = (structured_answer, matches, detected_language)
                self._add_to_cache(question, result)
                
                # Add to conversation memory
                clean_answer = structured_answer.get('answer', raw_response)
                self.conversation_memory.add_qa_pair(question, clean_answer, session_id)

                return result

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
                    'raw_response': raw_response,
                    'is_follow_up': is_follow_up
                }

                # Cache the result
                result = (structured_answer, matches, detected_language)
                self._add_to_cache(question, result)
                
                # Add to conversation memory
                self.conversation_memory.add_qa_pair(question, raw_response, session_id)

                return result

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
                'raw_response': error_msg,
                'is_follow_up': is_follow_up
            }
            result = (structured_error, [], "English")
            
            # Add to conversation memory
            self.conversation_memory.add_qa_pair(question, error_msg, session_id)
            
            # Cache the result
            self._add_to_cache(question, result)
            return result
    
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
    
    def get_conversation_context(self, session_id="default"):
        """Get current conversation context for a session."""
        history = self.conversation_memory.sessions.get(session_id, [])
        if not history:
            return {"qa_pairs": [], "count": 0}
        
        return {
            "qa_pairs": [{"question": qa["q"], "answer": qa["a"][:100] + "..." if len(qa["a"]) > 100 else qa["a"]} for qa in history],
            "count": len(history),
            "last_topic": history[-1]["q"] if history else None
        }
    
    def clear_conversation(self, session_id="default"):
        """Clear conversation memory for a session."""
        self.conversation_memory.clear_session(session_id)
        print(f"🗑️ Cleared conversation memory for session: {session_id}")
    
    def get_memory_stats(self):
        """Get conversation memory statistics."""
        return self.conversation_memory.get_stats()
    
    def translate_to_target_language(self, text, target_language):
        """Translate text to target language using LLM."""
        if target_language.lower() == 'english':
            return text
        
        try:
            translation_prompt = f"Translate the following text to {target_language}. Keep the meaning and tone exactly the same:\n\n{text}"
            response = self.llm.invoke(translation_prompt)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            print(f"⚠️ Translation error: {e}")
            return text  # Fallback to original text
    
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
            session_id = "interactive_session"
            print(f"💭 Using session: {session_id}")
            question = input("Enter your question (any language): ").strip()
            if question:
                result = rag_agent.generate_answer(question, session_id)
                if isinstance(result, tuple) and len(result) >= 3:
                    answer_data, matches, language = result
                    rag_agent.display_answer_with_sources(question, answer_data, matches, language)
                elif isinstance(result, tuple):
                    answer_data, matches = result
                    rag_agent.display_answer_with_sources(question, answer_data, matches)
                else:
                    print(f"\n🤖 Answer: {result}")
                
                # Show conversation context
                context = rag_agent.get_conversation_context(session_id)
                if context:
                    print(f"\n💭 Conversation Context: Last topic: {context.get('last_topic', 'None')}")
                    
                # Ask for follow-up
                while True:
                    follow_up = input("\nAsk a follow-up question (or 'quit' to exit): ").strip()
                    if follow_up.lower() in ['quit', 'exit', 'q']:
                        break
                    if follow_up:
                        result = rag_agent.generate_answer(follow_up, session_id)
                        if isinstance(result, tuple) and len(result) >= 3:
                            answer_data, matches, language = result
                            rag_agent.display_answer_with_sources(follow_up, answer_data, matches, language)
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
