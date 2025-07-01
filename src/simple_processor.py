"""
Simple Pinecone Data Processor for Kurzgesagt Transcripts
This script processes transcripts and creates JSON for later generating embeddings and uploading to Pinecone
"""

import os
import json
import uuid
from pathlib import Path
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.docstore.document import Document
from dotenv import load_dotenv

def main():
    print("🚀 Processing Kurzgesagt Transcripts for Pinecone")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    # Check if we have the API key
    api_key = os.getenv("PINECONE_API_KEY")
    if not api_key:
        print("❌ PINECONE_API_KEY not found in .env file")
        return
    else:
        print("✅ Pinecone API key found")
    
    # Check transcripts directory
    transcripts_dir = Path("transcripts")
    if not transcripts_dir.exists():
        print(f"❌ Transcripts directory not found: {transcripts_dir}")
        return
    
    transcript_files = list(transcripts_dir.glob("*.txt"))
    if not transcript_files:
        print(f"❌ No transcript files found in {transcripts_dir}")
        return
    
    print(f"📁 Found {len(transcript_files)} transcript files")
    
    # Initialize text splitter
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=80,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    
    # Process all transcript files
    print("\n📄 Processing transcripts...")
    all_chunks = []
    
    for file_path in transcript_files:
        print(f"  Processing: {file_path.name}")
        
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                print(f"    ⚠️ Empty file: {file_path.name}")
                continue
            
            # Create document
            video_title = file_path.stem.replace('_transcript', '').replace('_', ' ')
            doc = Document(
                page_content=content,
                metadata={
                    "source": file_path.name,
                    "video_title": video_title,
                    "file_path": str(file_path)
                }
            )
            
            # Split into chunks
            chunks = text_splitter.split_documents([doc])
            
            # Add chunk metadata
            for i, chunk in enumerate(chunks):
                chunk.metadata.update({
                    "chunk_id": f"{file_path.stem}_chunk_{i}",
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                })
            
            all_chunks.extend(chunks)
            print(f"    ✅ Created {len(chunks)} chunks")
            
        except Exception as e:
            print(f"    ❌ Error processing {file_path.name}: {e}")
            continue
    
    if not all_chunks:
        print("❌ No chunks were created!")
        return
    
    print(f"\n🧩 Total chunks created: {len(all_chunks)}")
    
    # Convert to Pinecone format
    print("\n💾 Converting to Pinecone format...")
    
    pinecone_records = []
    for chunk in all_chunks:
        record = {
            "id": str(uuid.uuid4()),
            "text": chunk.page_content,
            "metadata": chunk.metadata
        }
        pinecone_records.append(record)
    
    # Save to JSON file
    output_file = "pinecone_data.json"
    output_path = Path(output_file).resolve()
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(pinecone_records, f, indent=2, ensure_ascii=False)
    
    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    
    print("=" * 50)
    print("✅ SUCCESS! Data processed and saved")
    print(f"📄 Total documents: {len(transcript_files)}")
    print(f"🧩 Total chunks: {len(all_chunks)}")
    print(f"💾 JSON file: {output_file}")
    print(f"📊 File size: {file_size_mb:.2f} MB")
    print(f"📁 Full path: {output_path}")
    
    print("\n🎯 NEXT STEPS:")
    print("1. Go to Pinecone Console: https://app.pinecone.io")
    print("2. Create/select your index")
    print("3. Choose 'Work with raw text'")
    print("4. Select 'llama-text-embed-v2' embedding model")
    print("5. Set field map to: text")
    print("6. Set dimensions to: 1024")
    print("7. Upload the generated pinecone_data.json file")

if __name__ == "__main__":
    main()
