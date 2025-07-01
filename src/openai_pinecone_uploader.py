"""
OpenAI Embeddings + Pinecone Upload Script
Generate embeddings using OpenAI and upload to Pinecone index
"""

import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec
import uuid

def create_embeddings_and_upload():
    print("🚀 OpenAI Embeddings + Pinecone Upload")
    print("=" * 45)
    
    # Load environment variables
    load_dotenv()
    
    # Check API keys
    openai_key = os.getenv("OPENAI_API_KEY")
    pinecone_key = os.getenv("PINECONE_API_KEY")
    
    if not openai_key:
        print("❌ OPENAI_API_KEY not found in .env file")
        return
    if not pinecone_key:
        print("❌ PINECONE_API_KEY not found in .env file")
        return
    
    print("✅ Both API keys found")
    
    # Check if JSON file exists
    json_file = Path("pinecone_data.json")
    if not json_file.exists():
        print("❌ pinecone_data.json not found!")
        print("Run simple_processor.py first to generate the data")
        return
    
    # Load the JSON data
    print("📁 Loading pinecone_data.json...")
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"📊 Loaded {len(data)} text chunks")
    
    # Initialize OpenAI client
    print("🤖 Initializing OpenAI client...")
    openai_client = OpenAI(api_key=openai_key)
    
    # Initialize Pinecone
    print("🔧 Initializing Pinecone...")
    pc = Pinecone(api_key=pinecone_key)
    
    # Create or connect to index
    index_name = "kurzgesagt-transcripts"
    print(f"📋 Setting up index: {index_name}")
    
    # Check if index exists
    existing_indexes = [index.name for index in pc.list_indexes()]
    
    if index_name not in existing_indexes:
        print(f"🆕 Creating new index: {index_name}")
        pc.create_index(
            name=index_name,
            dimension=1536,  # OpenAI ada-002 embedding dimension
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"
            )
        )
        
        # Wait for index to be ready
        print("⏳ Waiting for index to be ready...")
        while not pc.describe_index(index_name).status['ready']:
            time.sleep(1)
        print("✅ Index is ready!")
    else:
        print(f"✅ Using existing index: {index_name}")
    
    # Connect to index
    index = pc.Index(index_name)
    
    # Generate embeddings and upload in batches
    print(f"\n🧠 Generating embeddings and uploading...")
    batch_size = 20  # Smaller batches for better error handling
    embedding_model = "text-embedding-ada-002"  # OpenAI's best embedding model
    
    total_batches = (len(data) + batch_size - 1) // batch_size
    successful_uploads = 0
    
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        batch_num = i // batch_size + 1
        
        print(f"📦 Processing batch {batch_num}/{total_batches} ({len(batch)} items)...")
        
        try:
            # Extract texts for embedding
            texts = [record["text"] for record in batch]
            
            # Generate embeddings using OpenAI
            print(f"   🧠 Generating embeddings...")
            response = openai_client.embeddings.create(
                model=embedding_model,
                input=texts
            )
            
            # Prepare vectors for Pinecone
            vectors = []
            for j, record in enumerate(batch):
                vector = {
                    "id": record["id"],
                    "values": response.data[j].embedding,
                    "metadata": {
                        **record["metadata"],
                        "text": record["text"][:1000]  # Truncate text in metadata to avoid size limits
                    }
                }
                vectors.append(vector)
            
            # Upload to Pinecone
            print(f"   📤 Uploading to Pinecone...")
            index.upsert(vectors=vectors)
            
            successful_uploads += len(batch)
            print(f"   ✅ Batch {batch_num} completed successfully!")
            
            # Small delay to avoid rate limits
            time.sleep(1)
            
        except Exception as e:
            print(f"   ❌ Error in batch {batch_num}: {e}")
            continue
    
    print(f"\n🎉 Upload completed!")
    print(f"✅ Successfully uploaded: {successful_uploads}/{len(data)} records")
    
    # Check final index stats
    print("\n📊 Final index statistics:")
    try:
        time.sleep(2)  # Wait for indexing to complete
        stats = index.describe_index_stats()
        print(f"   Total vectors: {stats.total_vector_count}")
        print(f"   Index dimension: {stats.dimension}")
        print(f"   Index fullness: {stats.index_fullness}")
    except Exception as e:
        print(f"   Could not get stats: {e}")
    
    print(f"\n✅ SUCCESS! Your Kurzgesagt transcripts are now searchable!")
    return index

def test_semantic_search(index=None):
    """Test semantic search functionality"""
    print("\n🔍 Testing Semantic Search")
    print("=" * 30)
    
    if not index:
        # Reconnect to index
        load_dotenv()
        pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        index = pc.Index("kurzgesagt-transcripts")
    
    # Initialize OpenAI for query embedding
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    # Test queries
    test_queries = [
        "How does the immune system work?",
        "What happens in a black hole?",
        "Nuclear energy and climate change",
        "Space exploration and aliens"
    ]
    
    for query in test_queries:
        print(f"\n🔎 Query: '{query}'")
        
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
                top_k=3,
                include_metadata=True
            )
            
            print(f"📋 Found {len(results.matches)} results:")
            for i, match in enumerate(results.matches, 1):
                video_title = match.metadata.get('video_title', 'Unknown')
                score = match.score
                text_preview = match.metadata.get('text', '')[:100] + "..."
                print(f"   {i}. {video_title}")
                print(f"      Score: {score:.3f}")
                print(f"      Preview: {text_preview}")
                print()
            
        except Exception as e:
            print(f"❌ Search failed: {e}")

def main():
    # Upload data with embeddings
    index = create_embeddings_and_upload()
    
    if index:
        # Ask if user wants to test search
        test_choice = input("\nWould you like to test semantic search? (y/n): ").strip().lower()
        if test_choice == 'y':
            test_semantic_search(index)
        
        print("\n🎯 Next Steps:")
        print("• Your index is ready for semantic search!")
        print("• Use the query interface or build your own search app")
        print("• The embeddings capture semantic meaning of the content")

if __name__ == "__main__":
    main()
