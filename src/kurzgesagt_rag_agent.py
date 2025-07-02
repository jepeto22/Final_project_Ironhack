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
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from typing import Any, Dict, Tuple, List
from .context_retriever import retrieve_context, format_context
from .language_utils import detect_language_and_translate
from .semantic_cache import SemanticCache
from .simple_conversation_memory import SimpleConversationMemory

class KurzgesagtRAGAgent:
    """
    Retrieval-Augmented Generation Agent for Kurzgesagt-style Q&A.
    Handles multilingual support, semantic caching, and simple conversation memory.
    """
    def __init__(self):
        load_dotenv()
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self.index = pc.Index("kurzgesagt-transcripts")
        self.llm = ChatOpenAI(
            model="gpt-4",
            temperature=0.7,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.response_schemas = [
            ResponseSchema(name="answer", description="The main answer to the question in the specified language"),
            ResponseSchema(name="confidence", description="Confidence level (high/medium/low) based on available context"),
            ResponseSchema(name="sources_used", description="Number of sources used to generate the answer"),
            ResponseSchema(name="language", description="The language of the response")
        ]
        self.output_parser = StructuredOutputParser.from_response_schemas(self.response_schemas)
        format_instructions = self.output_parser.get_format_instructions()
        self.rag_prompt = PromptTemplate(
            input_variables=["question", "context", "target_language"],
            template="""You are a knowledgeable science communicator inspired by Kurzgesagt's style.\n
            Your task is to answer questions using the provided context from Kurzgesagt videos.\n\n
            Guidelines:\n
            - Use ONLY the provided context to answer the question. Do not use external knowledge.\n
            - If the context doesn't contain enough information, say so clearly and return 'I can't answer that based on the available context.'\n
            - Always respond in the specified target language\n
            - Use simple language and analogies to explain complex concepts\n
            - Reference the relevant video titles explicitly in your answer\n
            - Be enthusiastic about science while remaining accurate\n
            - IMPORTANT: Answer in {target_language}. If the question is not in English, translate your response to match the language of the question.\n\n
            Context from Kurzgesagt videos:\n{context}\n\n
            Question: {question}\n\n{format_instructions}\n\n
            Provide your response in the specified JSON format:""",
            partial_variables={"format_instructions": format_instructions}
        )
        self.rick_prompt = PromptTemplate(
            input_variables=["question", "context", "target_language"],
            template=(
                "Wubba lubba dub dub! You're Rick Sanchez, the smartest scientist in the universe, *burp* and you're answering questions using context from some amateur science YouTube channel called Kurzgesagt. Whatever, Morty.\n\n"
                "Guidelines, Morty - pay attention because I'm only saying this once:\n"
                "- Use ONLY the provided context to answer, *burp* - I don't need to use my infinite knowledge for this basic stuff\n"
                "- If there's not enough info, just say \"Listen Morty, these bird animators didn't cover that topic, *burp* so I can't help you with their limited database\"\n"
                "- Answer in {target_language} because apparently we need to be *burp* multilingual now\n"
                "- Explain things like you're talking to Morty (aka an idiot) but with Rick's arrogance and burping\n"
                "- Reference the video titles but mock them a little bit\n"
                "- Be condescending about basic science concepts but still explain them correctly\n"
                "- Add random burps, \"Morty\"s, and Rick's catchphrases\n"
                "- Show disdain for the simplicity of the questions while still being helpful\n"
                "- IMPORTANT: Maintain Rick's personality while being scientifically accurate, *burp*\n\n"
                "Context from those Kurzgesagt nerds:\n{context}\n\n"
                "Question from some dimension where people ask obvious questions: {question}\n\n"
                "{format_instructions}\n\n"
                "*burp* Now give me the response in that boring JSON format they want:"
            ),
            partial_variables={"format_instructions": format_instructions}
        )
        self.rag_chain = self.rag_prompt | self.llm
        self.rick_chain = self.rick_prompt | self.llm
        self.semantic_cache = SemanticCache(similarity_threshold=0.90)
        self.conversation_memory = SimpleConversationMemory(max_history=4)

    def _get_embedding(self, query: str):
        """Generate embedding for a query."""
        try:
            query_response = self.openai_client.embeddings.create(
                model="text-embedding-ada-002",
                input=[query]
            )
            return query_response.data[0].embedding
        except Exception:
            return None

    def _get_from_cache(self, query: str):
        """Retrieve from semantic cache with similarity matching."""
        exact_match = self.semantic_cache.get_exact(query)
        if exact_match:
            return exact_match['results']
        query_embedding = self._get_embedding(query)
        if query_embedding:
            similar_match = self.semantic_cache.find_similar(query_embedding)
            if similar_match:
                _, results, _ = similar_match
                return results
        return None

    def _add_to_cache(self, query: str, results: Any):
        """Add to semantic cache with embedding."""
        query_embedding = self._get_embedding(query)
        if query_embedding:
            self.semantic_cache.add(query, query_embedding, results)

    def retrieve_context(self, query: str, top_k: int = 3):
        return retrieve_context(self.index, query, self.openai_client, top_k=top_k)

    def format_context(self, matches: List[Any]):
        return format_context(matches)

    def generate_answer(self, question: str, session_id: str = "default", max_tokens: int = 500, mode: str = "normal") -> Tuple[Dict, List, str]:
        """Generate answer using RAG with multilingual support, semantic caching, and simple conversation memory."""
        is_follow_up = self.conversation_memory.is_likely_followup(question)
        conversation_context = ""
        if is_follow_up:
            conversation_context = self.conversation_memory.get_recent_context(session_id, max_pairs=3)
        cache_key = f"{question}||MODE:{mode}"
        cached_result = self._get_from_cache(cache_key)
        if cached_result:
            answer_data, matches, language = cached_result
            clean_answer = answer_data.get('answer', str(answer_data)) if isinstance(answer_data, dict) else str(answer_data)
            self.conversation_memory.add_qa_pair(question, clean_answer, session_id)
            return cached_result
        try:
            detected_language, english_question = detect_language_and_translate(self.llm, question)
            matches = self.retrieve_context(english_question, top_k=3)
            if not matches:
                no_results_msg = "I couldn't find relevant information in the Kurzgesagt transcripts to answer your question."
                if detected_language.lower() != "english":
                    no_results_msg = self.translate_to_target_language(no_results_msg, detected_language)
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
                self.conversation_memory.add_qa_pair(question, no_results_msg, session_id)
                self._add_to_cache(cache_key, result)
                return result
            context = self.format_context(matches)
            sources = [match.metadata.get('video_title', 'Unknown') for match in matches]
            if is_follow_up and conversation_context:
                context = f"Recent conversation:\n{conversation_context}\n\nRelevant information:\n{context}"
            chain = self.rick_chain if mode == "crazy_scientist" else self.rag_chain
            raw_response = chain.invoke({
                "question": question,
                "context": context,
                "target_language": detected_language
            })
            if hasattr(raw_response, "content"):
                raw_response = raw_response.content
            try:
                parsed_response = self.output_parser.parse(raw_response)
                structured_answer = {
                    'answer': parsed_response.get('answer', raw_response),
                    'confidence': parsed_response.get('confidence', 'medium'),
                    'sources_used': parsed_response.get('sources_used', len(matches)),
                    'language': parsed_response.get('language', detected_language),
                    'sources': sources,
                    'raw_response': raw_response,
                    'is_follow_up': is_follow_up
                }
                result = (structured_answer, matches, detected_language)
                self._add_to_cache(cache_key, result)
                clean_answer = structured_answer.get('answer', raw_response)
                self.conversation_memory.add_qa_pair(question, clean_answer, session_id)
                return result
            except Exception:
                structured_answer = {
                    'answer': raw_response,
                    'confidence': 'medium',
                    'sources_used': len(matches),
                    'language': detected_language,
                    'sources': sources,
                    'raw_response': raw_response,
                    'is_follow_up': is_follow_up
                }
                result = (structured_answer, matches, detected_language)
                self._add_to_cache(cache_key, result)
                self.conversation_memory.add_qa_pair(question, raw_response, session_id)
                return result
        except Exception as e:
            error_msg = f"Error generating answer: {str(e)}"
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
            self.conversation_memory.add_qa_pair(question, error_msg, session_id)
            self._add_to_cache(cache_key, result)
            return result

    def get_conversation_context(self, session_id: str = "default") -> Dict:
        """Get current conversation context for a session."""
        history = self.conversation_memory.sessions.get(session_id, [])
        if not history:
            return {"qa_pairs": [], "count": 0}
        return {
            "qa_pairs": [
                {"question": qa["q"], "answer": qa["a"][:100] + "..." if len(qa["a"]) > 100 else qa["a"]}
                for qa in history
            ],
            "count": len(history),
            "last_topic": history[-1]["q"] if history else None
        }

    def clear_conversation(self, session_id: str = "default") -> None:
        """Clear conversation memory for a session."""
        self.conversation_memory.clear_session(session_id)

    def get_memory_stats(self) -> Dict:
        """Get conversation memory statistics."""
        return self.conversation_memory.get_stats()

    def translate_to_target_language(self, text: str, target_language: str) -> str:
        """Translate text to target language using LLM."""
        if target_language.lower() == 'english':
            return text
        try:
            translation_prompt = f"Translate the following text to {target_language}. Keep the meaning and tone exactly the same:\n\n{text}"
            response = self.llm.invoke(translation_prompt)
            return response.content if hasattr(response, 'content') else str(response)
        except Exception:
            return text

    def generate_rick_answer(self, question: str, session_id: str = "rick_session"):
        """Generate answers in Rick Sanchez mode."""
        return self.generate_answer(question, session_id, mode="crazy_scientist")

    def is_crazy_scientist_mode_available(self) -> bool:
        """Check if crazy scientist mode is properly initialized."""
        return hasattr(self, 'rick_chain') and self.rick_chain is not None
