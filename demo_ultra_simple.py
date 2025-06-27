"""
Demo: Ultra-Simple RAG System with Lightweight Conversation Memory
Shows how simple and effective the streamlined approach is
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'code'))

from kurzgesagt_rag_agent import KurzgesagtRAGAgent

def demo_simple_system():
    print("🚀 Ultra-Simple Kurzgesagt RAG Agent Demo")
    print("=" * 50)
    
    # Initialize the agent
    agent = KurzgesagtRAGAgent()
    
    # Demo conversation with follow-ups
    session_id = "demo_user"
    
    print("\n🗣️  Conversation Demo:")
    print("-" * 30)
    
    # First question - about black holes
    print("\n👤 User: What are black holes?")
    result1 = agent.generate_answer("What are black holes?", session_id=session_id)
    print(f"🤖 Agent: {result1[0]['answer'][:200]}...")
    
    # Follow-up question using pronouns
    print("\n👤 User: How big are they?")
    result2 = agent.generate_answer("How big are they?", session_id=session_id)
    print(f"🤖 Agent: {result2[0]['answer'][:200]}...")
    
    # Another follow-up
    print("\n👤 User: Tell me more")
    result3 = agent.generate_answer("Tell me more", session_id=session_id)
    print(f"🤖 Agent: {result3[0]['answer'][:200]}...")
    
    # New topic - should not use context
    print("\n👤 User: What is the immune system?")
    result4 = agent.generate_answer("What is the immune system?", session_id=session_id)
    print(f"🤖 Agent: {result4[0]['answer'][:200]}...")
    
    # Check conversation stats
    print(f"\n📊 Memory Stats: {agent.conversation_memory.get_stats()}")
    print(f"🗄️  Cache Stats: {agent.semantic_cache.get_stats()}")
    
    print("\n✅ Demo completed! The system is:")
    print("   • Ultra-simple (just 4 Q&A pairs in memory)")
    print("   • Fast (semantic caching)")
    print("   • Smart (detects follow-ups)")
    print("   • Multilingual (auto-detect & translate)")
    print("   • Production-ready!")

if __name__ == "__main__":
    demo_simple_system()
