# Kurzgesagt Video Analysis Project - Complete Roadmap

## Project Overview
Build an AI-powered system to download, transcribe, and analyze Kurzgesagt educational videos using vector databases and semantic search.

## 🎯 Project Goals
- Download audio from 31+ Kurzgesagt YouTube videos across 8 categories
- Transcribe audio to text using OpenAI Whisper
- Build a searchable vector database using Pinecone
- Create a query interface for semantic search across all content
- Enable intelligent Q&A about scientific topics covered in the videos

---

## 📋 Step-by-Step Implementation Guide

### Phase 1: Environment Setup (30 minutes)

#### 1.1 Install Required Software
```powershell
# Install Python packages
pip install openai-whisper yt-dlp pinecone-client langchain openai python-dotenv streamlit

# Install FFmpeg (required for audio processing)
# Option A: Download from https://ffmpeg.org/download.html
# Option B: Use package manager
winget install ffmpeg
# OR
choco install ffmpeg
```

#### 1.2 Get API Keys
- **OpenAI API Key**: https://platform.openai.com/api-keys
- **Pinecone API Key**: https://app.pinecone.io/ (free tier: 1 index, 1GB storage)

#### 1.3 Create Environment File
```bash
# Create .env file with your API keys
OPENAI_API_KEY=sk-your-openai-key-here
PINECONE_API_KEY=your-pinecone-key-here
PINECONE_ENVIRONMENT=gcp-starter
```

### Phase 2: Data Collection (1-2 hours)

#### 2.1 Prepare Video List
✅ **Already Done**: You have `video_selection.txt` with 31+ videos across 8 categories

#### 2.2 Download Audio Files
```powershell
# Run the batch downloader
python batch_audio_downloader.py
# Select option 1: Download all videos
```

**Expected Output**: 
- `audio_files/` folder with 31+ MP3 files
- Each file named after the video title

#### 2.3 Verify Downloads
```powershell
# Check audio files
dir audio_files\*.mp3
```

### Phase 3: Transcription (2-3 hours)

#### 3.1 Transcribe Audio to Text
The `batch_audio_downloader.py` script can handle transcription:
```powershell
# Run with transcription enabled
python batch_audio_downloader.py
# Select option 3: Download and transcribe all videos
```

**Expected Output**:
- `transcripts/` folder with 31+ TXT files
- Each transcript named `{video_title}_transcript.txt`

#### 3.2 Verify Transcriptions
```powershell
# Check transcript files
dir transcripts\*.txt
```

### Phase 4: Vector Database Creation (30 minutes)

#### 4.1 Build Pinecone Index
```powershell
# Create vector database from all transcripts
python pinecone_vector_store.py
```

**What this does**:
- Loads all transcript files
- Splits text into 1000-character chunks
- Creates embeddings using OpenAI
- Stores in Pinecone with metadata

#### 4.2 Verify Vector Store
The script will automatically test with a sample query and show results.

### Phase 5: Query Interface Development (1 hour)

#### 5.1 Create Simple Query Script
```python
# Create query_interface.py
from pinecone_vector_store import PineconeVectorStore

def search_videos(query, k=5):
    vs = PineconeVectorStore()
    results = vs.query_vector_store(query, k)
    
    for i, result in enumerate(results, 1):
        print(f"{i}. {result.metadata['video_title']}")
        print(f"   {result.page_content[:200]}...\n")

# Example usage
search_videos("How does the immune system fight bacteria?")
```

#### 5.2 Create Streamlit Web Interface (Optional)
```python
# Create app.py for web interface
import streamlit as st
from pinecone_vector_store import PineconeVectorStore

st.title("Kurzgesagt Video Search")
query = st.text_input("Ask a question about science:")

if query:
    vs = PineconeVectorStore()
    results = vs.query_vector_store(query, k=3)
    
    for result in results:
        st.subheader(result.metadata['video_title'])
        st.write(result.page_content)
```

### Phase 6: Advanced Features (Optional - 2-3 hours)

#### 6.1 RAG (Retrieval-Augmented Generation)
Create a chatbot that can answer questions using the video content:

```python
from langchain.chains import RetrievalQA
from langchain.llms import OpenAI

# Create Q&A system
llm = OpenAI(temperature=0)
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vector_store.as_retriever()
)

# Ask questions
answer = qa_chain.run("How do black holes form?")
```

#### 6.2 Category-Based Search
Add filtering by video categories (Aliens, Immune System, etc.)

#### 6.3 Semantic Clustering
Group similar content across videos to find related topics.

---

## 📁 Final Project Structure

```
Final_project_Ironhack/
├── .env                           # API keys
├── requirements.txt               # Python dependencies
├── README.md                      # Project documentation
├── video_selection.txt            # ✅ Video URLs list
├── batch_audio_downloader.py      # ✅ Download & transcribe
├── pinecone_vector_store.py       # ✅ Vector DB creation
├── simple_pinecone_builder.py     # ✅ Simple version
├── query_interface.py             # 🔄 Search interface
├── app.py                         # 🔄 Web interface (optional)
├── audio_files/                   # 🔄 Downloaded MP3s
│   ├── Fentanyl.mp3
│   ├── How_The_Immune_System_ACTUALLY_Works_IMMUNE.mp3
│   └── ... (31+ files)
├── transcripts/                   # 🔄 Text transcriptions
│   ├── Fentanyl_transcript.txt
│   ├── How_The_Immune_System_ACTUALLY_Works_IMMUNE_transcript.txt
│   └── ... (31+ files)
└── notebooks/                     # 🔄 Analysis notebooks (optional)
    ├── data_exploration.ipynb
    └── similarity_analysis.ipynb
```

**Legend**: ✅ Complete | 🔄 To Do

---

## 🚀 Quick Start Commands

1. **Setup Environment**:
   ```powershell
   pip install -r requirements.txt
   # Add API keys to .env file
   ```

2. **Download All Content**:
   ```powershell
   python batch_audio_downloader.py
   # Choose option 3 for download + transcription
   ```

3. **Build Vector Database**:
   ```powershell
   python pinecone_vector_store.py
   ```

4. **Start Searching**:
   ```powershell
   python query_interface.py
   ```

---

## 📊 Expected Deliverables

### Core Deliverables
- [ ] 31+ audio files downloaded
- [ ] 31+ transcript files generated
- [ ] Pinecone vector database with searchable content
- [ ] Query interface for semantic search
- [ ] Documentation and README

### Optional Advanced Features
- [ ] Web interface with Streamlit
- [ ] RAG-based Q&A system
- [ ] Category-based filtering
- [ ] Content similarity analysis
- [ ] Export functionality for search results

---

## ⏱️ Time Estimates

| Phase | Task | Time | Complexity |
|-------|------|------|------------|
| 1 | Environment Setup | 30 min | Easy |
| 2 | Audio Download | 1-2 hours | Easy |
| 3 | Transcription | 2-3 hours | Medium |
| 4 | Vector Database | 30 min | Medium |
| 5 | Query Interface | 1 hour | Medium |
| 6 | Advanced Features | 2-3 hours | Hard |

**Total Core Project**: 4-6 hours
**With Advanced Features**: 6-9 hours

---

## 🔧 Troubleshooting

### Common Issues
1. **FFmpeg not found**: Install FFmpeg and add to PATH
2. **API key errors**: Check .env file format and key validity
3. **Pinecone quota exceeded**: Use free tier limits wisely
4. **Download failures**: Some videos may be geo-blocked or unavailable
5. **Transcription errors**: Whisper needs sufficient disk space and RAM

### Performance Tips
- Use smaller Whisper models for faster transcription (`tiny`, `base`)
- Process videos in batches to avoid API rate limits
- Monitor Pinecone usage to stay within free tier

---

## 📈 Success Metrics

- ✅ Successfully download 90%+ of target videos
- ✅ Generate accurate transcripts with <5% word error rate
- ✅ Create searchable vector database with semantic relevance
- ✅ Enable natural language queries about scientific content
- ✅ Response time <3 seconds for typical queries

---

## 🎓 Learning Outcomes

By completing this project, you'll gain experience with:
- **Audio Processing**: yt-dlp, FFmpeg, Whisper
- **NLP**: Text processing, embeddings, semantic search
- **Vector Databases**: Pinecone, similarity search
- **LLM Integration**: OpenAI API, RAG systems
- **Python Development**: API integration, error handling, modular code

Good luck with your project! 🚀
