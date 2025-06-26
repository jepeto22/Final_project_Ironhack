"""
Cache Manager Module
Handles in-memory caching for the Kurzgesagt RAG Agent.
"""

class CacheManager:
    def __init__(self):
        self.cache = {}

    def get(self, key):
        """Retrieve an item from the cache."""
        return self.cache.get(key)

    def add(self, key, value):
        """Add an item to the cache."""
        self.cache[key] = value
