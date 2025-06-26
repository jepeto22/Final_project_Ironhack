"""
Context Retriever Module
Handles context retrieval and formatting for the Kurzgesagt RAG Agent.
"""

def retrieve_context(index, query, openai_client, cache, top_k=5):
    """Retrieve relevant context from Pinecone, with caching and post-filtering."""
    # Check cache first
    cached_result = cache.get(query)
    if cached_result:
        print("🔄 Using cached context for query.")
        return cached_result

    try:
        # Generate embedding for query
        query_response = openai_client.embeddings.create(
            model="text-embedding-ada-002",
            input=[query]
        )
        query_embedding = query_response.data[0].embedding

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

        # Cache the result
        cache[query] = filtered_matches

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
