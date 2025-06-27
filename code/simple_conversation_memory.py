"""
Simple Conversation Memory
Ultra-lightweight solution for handling follow-up questions with recent conversation history
Just keeps the last few Q&A pairs per session - nothing fancy!
"""

from typing import List, Dict, Optional
from datetime import datetime

class SimpleConversationMemory:
    """Ultra-simple conversation memory that keeps track of recent Q&A pairs."""
    
    def __init__(self, max_history: int = 4):
        """Initialize with max_history Q&A pairs to keep (default: 4)."""
        self.sessions = {}  # session_id -> list of {'q': str, 'a': str, 'time': datetime}
        self.max_history = max_history
    
    def add_qa_pair(self, question: str, answer: str, session_id: str = "default"):
        """Add a Q&A pair to session history."""
        if session_id not in self.sessions:
            self.sessions[session_id] = []
        
        # Add new Q&A (keep it simple!)
        self.sessions[session_id].append({
            'q': question,
            'a': answer[:300] + "..." if len(answer) > 300 else answer,  # Truncate long answers
            'time': datetime.now()
        })
        
        # Keep only the last max_history pairs
        if len(self.sessions[session_id]) > self.max_history:
            self.sessions[session_id] = self.sessions[session_id][-self.max_history:]
    
    def get_recent_context(self, session_id: str = "default", max_pairs: int = 2) -> str:
        """Get recent Q&A context as formatted string for the LLM."""
        history = self.sessions.get(session_id, [])
        if not history:
            return ""
        
        # Get the most recent pairs
        recent = history[-max_pairs:]
        context_parts = []
        
        for i, qa in enumerate(recent, 1):
            context_parts.append(f"Recent Q{i}: {qa['q']}")
            context_parts.append(f"Recent A{i}: {qa['a']}")
        
        return "\n".join(context_parts)
    
    def is_likely_followup(self, question: str) -> bool:
        """Simple check if question might be a follow-up (pronouns, short questions, etc.)."""
        q = question.lower().strip()
        
        # Very short questions (1-2 words) are often follow-ups
        words = q.split()
        if len(words) <= 2:
            return True
        
        # Common follow-up patterns
        followup_patterns = [
            'tell me more', 'more about', 'what about', 'how about',
            'and what', 'but what', 'also'
        ]
        
        # Pronouns that suggest reference to previous context
        # Check if they appear at the start or are prominent
        pronouns = ['it', 'that', 'this', 'they', 'them', 'those', 'these']
        
        for pattern in followup_patterns:
            if pattern in q:
                return True
        
        # Check for pronouns at the beginning or after common question words
        for pronoun in pronouns:
            if q.startswith(pronoun + ' ') or q.startswith('what ' + pronoun) or q.startswith('how ' + pronoun):
                return True
        
        return False
    
    def clear_session(self, session_id: str = "default"):
        """Clear conversation history for a session."""
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    def get_stats(self) -> Dict:
        """Get simple statistics."""
        total_pairs = sum(len(history) for history in self.sessions.values())
        return {
            'active_sessions': len(self.sessions),
            'total_qa_pairs': total_pairs,
            'max_history_per_session': self.max_history
        }
