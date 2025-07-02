"""
Semantic Cache Module
Alternative lightweight implementation without scikit-learn dependency.
Provides a cache for query results with semantic similarity matching.
"""

import re
import numpy as np


def cosine_similarity_manual(vec1, vec2):
    """Calculate cosine similarity between two vectors manually."""
    a = np.array(vec1)
    b = np.array(vec2)
    dot_product = np.dot(a, b)
    magnitude_a = np.linalg.norm(a)
    magnitude_b = np.linalg.norm(b)
    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0
    return dot_product / (magnitude_a * magnitude_b)


def normalize_query(query):
    """Normalize query text for better matching."""
    return re.sub(r"\s+", " ", query.lower()).strip()


class SemanticCache:
    """
    Enhanced cache with semantic similarity matching.
    Stores queries, their embeddings, and results for fast retrieval.
    """

    def __init__(self, similarity_threshold=0.9):
        self._cache = {}
        self.similarity_threshold = similarity_threshold

    def _calculate_similarity(self, embedding1, embedding2):
        """Calculate similarity between embeddings."""
        return cosine_similarity_manual(embedding1, embedding2)

    def find_similar(self, query_embedding):
        """
        Find the most similar cached query above the similarity threshold.
        Returns (cached_query, results, similarity) or None if not found.
        """
        best_match = None
        best_similarity = 0.0
        for cached_query, cached_data in self._cache.items():
            embedding = cached_data.get("embedding")
            if embedding is not None:
                similarity = self._calculate_similarity(query_embedding, embedding)
                if (
                    similarity > best_similarity
                    and similarity >= self.similarity_threshold
                ):
                    best_similarity = similarity
                    best_match = (cached_query, cached_data["results"], similarity)
        return best_match

    def add(self, query, embedding, results):
        """Add a query, its embedding, and results to the cache."""
        self._cache[query] = {
            "embedding": embedding,
            "results": results,
            "normalized_query": normalize_query(query),
        }

    def get_exact(self, query):
        """Get exact match from cache by query string."""
        return self._cache.get(query)

    def clear(self):
        """Clear the cache."""
        self._cache.clear()

    def size(self):
        """Get the number of cached queries."""
        return len(self._cache)

    def get_stats(self):
        """Get cache statistics as a dictionary."""
        return {
            "total_queries": len(self._cache),
            "threshold": self.similarity_threshold,
        }
