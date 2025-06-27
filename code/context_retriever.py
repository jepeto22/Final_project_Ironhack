"""
Context Retriever Module
Handles context retrieval and formatting for the Kurzgesagt RAG Agent.
"""

import numpy as np

def cosine_similarity_simple(vec1, vec2):
    """Calculate cosine similarity between two vectors."""
    a = np.array(vec1)
    b = np.array(vec2)
    
    dot_product = np.dot(a, b)
    magnitude_a = np.linalg.norm(a)
    magnitude_b = np.linalg.norm(b)
    
    if magnitude_a == 0 or magnitude_b == 0:
        return 0
    
    return dot_product / (magnitude_a * magnitude_b)

def get_query_embedding(query, openai_client):
    """Generate embedding for a query."""
    try:
        query_response = openai_client.embeddings.create(
            model="text-embedding-ada-002",
            input=[query]
        )
        return query_response.data[0].embedding
    except Exception as e:
        print(f"❌ Embedding error: {e}")
        return None

def find_similar_cached_query(query, openai_client, cache, similarity_threshold=0.85):
    """Find a similar query in cache using semantic similarity."""
    if not cache:
        return None, None
    
    # Get embedding for current query
    query_embedding = get_query_embedding(query, openai_client)
    if query_embedding is None:
        return None, None
    
    best_match = None
    best_similarity = 0
    
    # Check similarity with cached queries
    for cached_query, cached_data in cache.items():
        if isinstance(cached_data, dict) and 'embedding' in cached_data:
            cached_embedding = cached_data['embedding']
            
            # Calculate cosine similarity
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

def retrieve_context(index, query, openai_client, semantic_cache=None, top_k=5):
    """Retrieve relevant context from Pinecone with optional semantic caching."""
    
    try:
        print("🚀 Performing Pinecone search...")
        
        # Generate embedding for query
        query_embedding = get_query_embedding(query, openai_client)
        if query_embedding is None:
            return []

        # Search Pinecone
        results = index.query(
            vector=query_embedding,
            top_k=top_k * 2,  # Retrieve more results for filtering
            include_metadata=True
        )

        # Post-filtering: Ensure relevance threshold
        filtered_matches = [
            match for match in results.matches
            if match.score >= 0.75  # Adjust threshold as needed
        ][:top_k]  # Limit to top_k after filtering

        print(f"📚 Found {len(filtered_matches)} relevant segments after filtering")
        return filtered_matches

    except Exception as e:
        print(f"❌ Retrieval error: {e}")
        return []

def format_context(matches):
    """Format retrieved context for the LLM with improved clarity."""
    if not matches:
        return "No relevant context found."

    context_parts = []
    for i, match in enumerate(matches, 1):
        video_title = match.metadata.get('video_title', 'Unknown')
        text = match.metadata.get('text', 'No content available')
        score = match.score

        context_part = f"""
Context {i} (Relevance: {score:.3f}):
Video Title: {video_title}
Content Snippet: {text[:200]}...  # Limit snippet length for clarity
"""
        context_parts.append(context_part.strip())

    return "\n\n".join(context_parts)
