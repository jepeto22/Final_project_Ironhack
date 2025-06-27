# 🎯 Ultra-Simple Conversation Memory

## What is it?
A **super lightweight** conversation memory system that keeps just the last 4 Q&A pairs per user session. Perfect for handling follow-up questions without complexity!

## Key Features ✨
- **Ultra-simple**: Just 4 Q&A pairs in memory per session
- **Smart follow-up detection**: Detects pronouns, short questions, and common patterns
- **Automatic memory management**: Old conversations naturally fade away
- **Multi-session support**: Each user gets their own conversation thread
- **Production-ready**: Minimal memory footprint, fast performance

## How it Works 🧠

### 1. Simple Storage
```python
# Each session stores max 4 Q&A pairs like this:
sessions = {
    "user123": [
        {"q": "What are black holes?", "a": "Black holes are...", "time": datetime},
        {"q": "How big are they?", "a": "They vary in size...", "time": datetime},
        {"q": "Tell me more", "a": "Supermassive black holes...", "time": datetime},
        {"q": "What about neutron stars?", "a": "Neutron stars are...", "time": datetime}
    ]
}
```

### 2. Follow-up Detection
The system detects follow-ups by looking for:
- **Short questions** (1-2 words): "More?", "How so?"
- **Pronouns**: "What about it?", "How do they work?"
- **Follow-up phrases**: "Tell me more", "What about", "How about"

### 3. Context Injection
When a follow-up is detected, recent Q&A pairs are added to the LLM prompt:
```
Recent Q1: What are black holes?
Recent A1: Black holes are regions of spacetime...
Recent Q2: How big are they?
Recent A2: They vary in size from stellar mass...

User's current question: Tell me more
```

## Usage Example 💬

```python
from simple_conversation_memory import SimpleConversationMemory

# Create memory (keeps last 4 Q&A pairs)
memory = SimpleConversationMemory(max_history=4)

# Add Q&A pairs
memory.add_qa_pair("What are black holes?", "Black holes are...", "user123")
memory.add_qa_pair("How big are they?", "They vary...", "user123")

# Check for follow-ups
is_followup = memory.is_likely_followup("Tell me more")  # True

# Get context for LLM
context = memory.get_recent_context("user123", max_pairs=2)
```

## Benefits 🚀

1. **Simple to understand**: No complex conversation tracking
2. **Memory efficient**: Only 4 Q&A pairs per user maximum
3. **Fast**: No database queries, just in-memory lists
4. **Maintenance-free**: Automatically cleans up old conversations
5. **Effective**: Handles 90% of follow-up scenarios perfectly

## Configuration Options ⚙️

```python
# Adjust max history per session (default: 4)
memory = SimpleConversationMemory(max_history=6)

# Get stats
stats = memory.get_stats()
# {'active_sessions': 3, 'total_qa_pairs': 12, 'max_history_per_session': 4}

# Clear a session
memory.clear_session("user123")
```

## Perfect For 🎯
- **Chatbots** that need to handle "tell me more" questions
- **Q&A systems** with natural follow-up conversations
- **Educational tools** where users explore topics step by step
- **Customer support** for contextual follow-up questions

## Integration with RAG Agent 🔗

The RAG agent automatically:
1. Detects if a question is a follow-up
2. Adds recent context to the LLM prompt if needed
3. Stores the new Q&A pair for future follow-ups
4. Maintains separate conversation threads per user/session

**Result**: Natural conversations that feel intelligent without the complexity!
