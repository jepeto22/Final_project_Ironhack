import whisper
import yt_dlp
import os
import re
from pathlib import Path
import time

def extract_urls_from_file(file_path):
    """Extract YouTube URLs from the video selection file"""
    urls = []
    titles = []
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Regex pattern to match YouTube URLs and their descriptions
    pattern = r'- (https://www\.youtube\.com/watch\?v=[^&\s]+).*?--> (.+)'
    matches = re.findall(pattern, content)
    
    for url, title in matches:
        # Clean the URL (remove list parameters to get direct video URL)
        clean_url = url.split('&list=')[0]
        urls.append(clean_url)
        # Clean the title for filename
        clean_title = re.sub(r'[^\w\s-]', '', title.strip()).strip()
        clean_title = re.sub(r'[-\s]+', '_', clean_title)
        titles.append(clean_title)
    
    return urls, titles

def download_audio(video_url, output_dir, filename):
    """Download audio from a YouTube video"""
    output_path = os.path.join(output_dir, f"{filename}.%(ext)s")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': output_path,
        'ffmpeg_location': 'C:\\FFmpeg\\bin', 
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"Downloading: {filename}...")
            ydl.download([video_url])
            print(f"✓ Downloaded: {filename}")
            return True
    except Exception as e:
        print(f"✗ Error downloading {filename}: {str(e)}")
        return False

def transcribe_audio_whisper_local(audio_path, model_size="small"):
    """Transcribe audio using Whisper"""
    try:
        model = whisper.load_model(model_size)
        result = model.transcribe(audio_path)
        return result["text"]
    except Exception as e:
        print(f"Error transcribing {audio_path}: {str(e)}")
        return None

def batch_download_and_transcribe(video_file_path, output_dir="audio_files", transcripts_dir="transcripts", model_size="small"):
    """Download audio from multiple videos and optionally transcribe them"""
    
    # Create output directories
    Path(output_dir).mkdir(exist_ok=True)
    Path(transcripts_dir).mkdir(exist_ok=True)
    
    # Extract URLs and titles from file
    urls, titles = extract_urls_from_file(video_file_path)
    
    print(f"Found {len(urls)} videos to download")
    print("-" * 50)
    
    successful_downloads = 0
    failed_downloads = 0
    
    for i, (url, title) in enumerate(zip(urls, titles), 1):
        print(f"\n[{i}/{len(urls)}] Processing: {title}")
        
        # Check if audio file already exists
        audio_file_path = os.path.join(output_dir, f"{title}.mp3")
        
        if os.path.exists(audio_file_path):
            print(f"Audio file already exists: {title}.mp3")
        else:
            # Download audio
            success = download_audio(url, output_dir, title)
            if success:
                successful_downloads += 1
            else:
                failed_downloads += 1
                continue
        
        # Transcribe audio
        transcript_file_path = os.path.join(transcripts_dir, f"{title}_transcript.txt")
        if not os.path.exists(transcript_file_path):
            print(f"Transcribing: {title}...")
            transcript = transcribe_audio_whisper_local(audio_file_path, model_size)
            if transcript:
                with open(transcript_file_path, "w", encoding="utf-8") as f:
                    f.write(transcript)
                print(f"✓ Transcript saved: {title}_transcript.txt")
        else:
            print(f"Transcript already exists: {title}_transcript.txt")
        
        # Add a small delay to be respectful to YouTube's servers
        time.sleep(1)
    
    print("\n" + "=" * 50)
    print(f"Download Summary:")
    print(f"✓ Successful downloads: {successful_downloads}")
    print(f"✗ Failed downloads: {failed_downloads}")
    print(f"Total videos processed: {len(urls)}")
    print(f"Audio files saved in: {output_dir}")

def download_specific_categories(video_file_path, categories=None, output_dir="audio_files"):
    """Download audio only from specific categories"""
    
    # Create output directory
    Path(output_dir).mkdir(exist_ok=True)
    
    with open(video_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if categories is None:
        categories = ["Black Holes", "Climate change", "Aliens", "Drugs", "Dinosaurs", "Immune system", "What if scenarios"]
    
    for category in categories:
        print(f"\n--- Processing category: {category} ---")
        
        # Find the category section
        category_pattern = rf'{re.escape(category)}:(.*?)(?=\n\d+\.|$)'
        category_match = re.search(category_pattern, content, re.DOTALL)
        
        if not category_match:
            print(f"Category '{category}' not found")
            continue
        
        category_content = category_match.group(1)
        
        # Extract URLs and titles from this category
        pattern = r'- (https://www\.youtube\.com/watch\?v=[^&\s]+).*?--> (.+)'
        matches = re.findall(pattern, category_content)
        
        for url, title in matches:
            clean_url = url.split('&list=')[0]
            clean_title = re.sub(r'[^\w\s-]', '', title.strip()).strip()
            clean_title = re.sub(r'[-\s]+', '_', clean_title)
            
            # Add category prefix to filename
            filename = f"{category.replace(' ', '_')}_{clean_title}"
            
            success = download_audio(clean_url, output_dir, filename)
            time.sleep(1)

if __name__ == "__main__":
    video_file = "video_selection.txt"
    
    print("YouTube Audio Batch Downloader")
    print("=" * 40)
    print("1. Download all videos")
    print("2. Download specific categories")
    print("3. Download and transcribe all videos")
    
    choice = input("\nSelect option (1-3): ").strip()
    
    if choice == "1":
        batch_download_and_transcribe(video_file)
    elif choice == "2":
        print("\nAvailable categories:")
        categories = ["Black Holes", "Climate change", "Aliens", "Drugs", "Dinosaurs", "Immune system", "What if scenarios"]
        for i, cat in enumerate(categories, 1):
            print(f"{i}. {cat}")
        
        selected = input("\nEnter category numbers (comma-separated, e.g., 1,3,5): ").strip()
        try:
            indices = [int(x.strip()) - 1 for x in selected.split(',')]
            selected_categories = [categories[i] for i in indices if 0 <= i < len(categories)]
            download_specific_categories(video_file, selected_categories)
        except:
            print("Invalid selection")
    elif choice == "3":
        print("This will download audio files and create transcripts (may take a while)...")
        confirm = input("Continue? (y/N): ").strip().lower()
        if confirm == 'y':
            batch_download_and_transcribe(video_file)
    else:
        print("Invalid choice")
