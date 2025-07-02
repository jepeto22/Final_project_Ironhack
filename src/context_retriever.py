"""
Context Retriever Module
Handles context retrieval and formatting for the Kurzgesagt RAG Agent.
"""

from typing import Any, Dict, List, Optional, Tuple
import numpy as np

def cosine_similarity_simple(vec1: List[float], vec2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    a = np.array(vec1)
    b = np.array(vec2)
    dot_product = np.dot(a, b)
    magnitude_a = np.linalg.norm(a)
    magnitude_b = np.linalg.norm(b)
    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0
    return float(dot_product / (magnitude_a * magnitude_b))

def get_query_embedding(query: str, openai_client: Any) -> Optional[List[float]]:
    """Generate embedding for a query using the OpenAI client."""
    try:
        query_response = openai_client.embeddings.create(
            model="text-embedding-ada-002",
            input=[query]
        )
        return query_response.data[0].embedding
    except Exception as e:
        print(f"❌ Embedding error: {e}")
        return None

def find_similar_cached_query(
    query: str,
    openai_client: Any,
    cache: Dict[str, Dict[str, Any]],
    similarity_threshold: float = 0.85
) -> Tuple[Optional[str], Optional[Any]]:
    """Find a similar query in cache using semantic similarity."""
    if not cache:
        return None, None
    query_embedding = get_query_embedding(query, openai_client)
    if query_embedding is None:
        return None, None
    best_match = None
    best_similarity = 0.0
    for cached_query, cached_data in cache.items():
        if isinstance(cached_data, dict) and 'embedding' in cached_data:
            cached_embedding = cached_data['embedding']
            similarity = cosine_similarity_simple(query_embedding, cached_embedding)
            print(f"🔍 Similarity with '{cached_query[:50]}...': {similarity:.3f}")
            if similarity > best_similarity and similarity >= similarity_threshold:
                best_similarity = similarity
                best_match = (cached_query, cached_data['results'])
    if best_match:
        cached_query, results = best_match
        print(f"🎯 Found similar cached query: '{cached_query[:50]}...' (similarity: {best_similarity:.3f})")
        return cached_query, results
    return None, None

def retrieve_context(
    index: Any,
    query: str,
    openai_client: Any,
    top_k: int = 3
) -> List[Any]:
    """Retrieve relevant context from Pinecone."""
    try:
        print("🚀 Performing Pinecone search...")
        query_embedding = get_query_embedding(query, openai_client)
        if query_embedding is None:
            return []
        results = index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True
        )
        filtered_matches = [
            match for match in results.matches
            if match.score >= 0.75
        ][:top_k]
        return filtered_matches
    except Exception as e:
        print(f"❌ Retrieval error: {e}")
        return []

def format_context(matches: List[Any]) -> str:
    """Format retrieved context for the LLM with improved clarity."""
    if not matches:
        return "No relevant context found."
    context_parts = []
    for i, match in enumerate(matches, 1):
        video_title = match.metadata.get('video_title', 'Unknown')
        text = match.metadata.get('text', 'No content available')
        score = match.score
        context_part = (
            f"Context {i} (Relevance: {score:.3f}):\n"
            f"Video Title: {video_title}\n"
            f"Content Snippet: {text[:200]}...  # Limit snippet length for clarity"
        )
        context_parts.append(context_part)
    return "\n\n".join(context_parts)
