"""
Semantic Cache Module
Alternative lightweight implementation without scikit-learn dependency
"""

import numpy as np
import math

def cosine_similarity_manual(vec1, vec2):
    """Calculate cosine similarity between two vectors manually."""
    # Convert to numpy arrays
    a = np.array(vec1)
    b = np.array(vec2)
    
    # Calculate dot product
    dot_product = np.dot(a, b)
    
    # Calculate magnitudes
    magnitude_a = np.linalg.norm(a)
    magnitude_b = np.linalg.norm(b)
    
    # Avoid division by zero
    if magnitude_a == 0 or magnitude_b == 0:
        return 0
    
    # Calculate cosine similarity
    return dot_product / (magnitude_a * magnitude_b)

def normalize_query(query):
    """Normalize query text for better matching."""
    import re
    # Convert to lowercase and remove extra whitespace
    query = query.lower().strip()
    # Remove punctuation and normalize spaces
    query = re.sub(r'[^\w\s]', '', query)
    query = re.sub(r'\s+', ' ', query)
    return query

class SemanticCache:
    """Enhanced cache with semantic similarity matching."""
    
    def __init__(self, similarity_threshold=0.9):
        self.cache = {}
        self.similarity_threshold = similarity_threshold
        
    def _calculate_similarity(self, embedding1, embedding2):
        """Calculate similarity between embeddings."""
        return cosine_similarity_manual(embedding1, embedding2)
    
    def find_similar(self, query_embedding, openai_client=None):
        """Find similar cached queries."""
        best_match = None
        best_similarity = 0
        
        for cached_query, cached_data in self.cache.items():
            if 'embedding' in cached_data:
                similarity = self._calculate_similarity(
                    query_embedding, 
                    cached_data['embedding']
                )
                
                if similarity > best_similarity and similarity >= self.similarity_threshold:
                    best_similarity = similarity
                    best_match = (cached_query, cached_data['results'], similarity)
        
        return best_match
    
    def add(self, query, embedding, results):
        """Add query to cache with embedding."""
        self.cache[query] = {
            'embedding': embedding,
            'results': results,
            'normalized_query': normalize_query(query)
        }
    
    def get_exact(self, query):
        """Get exact match from cache."""
        return self.cache.get(query)
    
    def clear(self):
        """Clear the cache."""
        self.cache.clear()
    
    def size(self):
        """Get cache size."""
        return len(self.cache)
    
    def get_stats(self):
        """Get cache statistics."""
        return {
            'total_queries': len(self.cache),
            'threshold': self.similarity_threshold
        }
