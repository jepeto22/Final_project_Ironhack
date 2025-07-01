# Kurzgesagt RAG Agent Package
# This package contains the core functionality for the Kurzgesagt RAG system

__version__ = "1.0.0"
__author__ = "Kurzgesagt RAG Team"

# Import main components for easy access
from .kurzgesagt_rag_agent import KurzgesagtRAGAgent
from .context_retriever import retrieve_context, format_context
from .language_utils import detect_language_and_translate
from .semantic_cache import SemanticCache
from .simple_conversation_memory import SimpleConversationMemory

__all__ = [
    'KurzgesagtRAGAgent',
    'retrieve_context', 
    'format_context',
    'detect_language_and_translate',
    'SemanticCache',
    'SimpleConversationMemory'
]
