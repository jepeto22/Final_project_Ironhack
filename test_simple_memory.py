"""
Test the ultra-simple conversation memory system
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

from simple_conversation_memory import SimpleConversationMemory

def test_simple_memory():
    print("🧪 Testing Ultra-Simple Conversation Memory")
    print("=" * 50)
    
    # Create memory with max 4 Q&A pairs
    memory = SimpleConversationMemory(max_history=4)
    
    # Simulate a conversation
    session_id = "test_user"
    
    # Add some Q&A pairs
    memory.add_qa_pair("What are black holes?", "Black holes are regions of spacetime where gravity is so strong that nothing can escape...", session_id)
    
    memory.add_qa_pair("How do they form?", "Black holes form when massive stars collapse under their own gravity at the end of their lives...", session_id)
    
    memory.add_qa_pair("What about supermassive ones?", "Supermassive black holes are found at the centers of galaxies and can contain millions or billions of solar masses...", session_id)
    
    print(f"\n📊 Current stats: {memory.get_stats()}")
    
    # Test follow-up detection
    test_questions = [
        "What are quasars?",  # Not a follow-up
        "Tell me more",       # Follow-up
        "What about it?",     # Follow-up
        "How big are they?",  # Follow-up
        "Explain neutron stars", # Not a follow-up
    ]
    
    print("\n🔍 Testing Follow-up Detection:")
    for q in test_questions:
        is_followup = memory.is_likely_followup(q)
        print(f"  '{q}' -> {'✅ Follow-up' if is_followup else '❌ New topic'}")
    
    # Test context retrieval
    print("\n💭 Recent conversation context:")
    context = memory.get_recent_context(session_id, max_pairs=2)
    print(context)
    
    # Add one more to test the limit
    memory.add_qa_pair("Are there other types?", "Yes, there are stellar black holes, intermediate black holes, and primordial black holes...", session_id)
    
    print(f"\n📊 After adding 4th pair: {memory.get_stats()}")
    
    # Add 5th to test truncation
    memory.add_qa_pair("What happens if you fall into one?", "Due to tidal forces, you would be stretched out in a process called spaghettification...", session_id)
    
    print(f"\n📊 After adding 5th pair (should still be 4): {memory.get_stats()}")
    
    print("\n💭 Final conversation context (should be last 2 pairs):")
    context = memory.get_recent_context(session_id, max_pairs=2)
    print(context)
    
    print("\n✅ Simple memory test completed!")

if __name__ == "__main__":
    test_simple_memory()
