"""
Batch YouTube Audio Downloader and Transcriber
Downloads audio from YouTube videos and optionally transcribes them using Whisper.
"""

import os
import re
import time
from pathlib import Path
from typing import List, Optional, Tuple

import whisper
import yt_dlp

DEFAULT_OUTPUT_DIR = "audio_files"
DEFAULT_TRANSCRIPTS_DIR = "transcripts"
DEFAULT_VIDEO_FILE = "video_selection.txt"
DEFAULT_MODEL_SIZE = "small"
DEFAULT_CATEGORIES = [
    "Black Holes", "Climate change", "Aliens", "Drugs",
    "Dinosaurs", "Immune system", "What if scenarios"
]

def extract_urls_from_file(file_path: str) -> Tuple[List[str], List[str]]:
    """Extract YouTube URLs and titles from the video selection file."""
    urls = []
    titles = []
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    pattern = r'- (https://www\.youtube\.com/watch\?v=[^&\s]+).*?--> (.+)'
    matches = re.findall(pattern, content)
    for url, title in matches:
        clean_url = url.split('&list=')[0]
        urls.append(clean_url)
        clean_title = re.sub(r'[^\w\s-]', '', title.strip()).strip()
        clean_title = re.sub(r'[-\s]+', '_', clean_title)
        titles.append(clean_title)
    return urls, titles

def download_audio(video_url: str, output_dir: str, filename: str) -> bool:
    """Download audio from a YouTube video."""
    output_path = str(Path(output_dir) / f"{filename}.%(ext)s")
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
    except yt_dlp.utils.DownloadError as e:
        print(f"✗ Error downloading {filename}: {str(e)}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error downloading {filename}: {str(e)}")
        return False

def transcribe_audio_whisper_local(audio_path: str, model_size: str = DEFAULT_MODEL_SIZE) -> Optional[str]:
    """Transcribe audio using Whisper."""
    try:
        model = whisper.load_model(model_size)
        result = model.transcribe(audio_path)
        return result["text"]
    except Exception as e:
        print(f"Error transcribing {audio_path}: {str(e)}")
        return None

def batch_download_and_transcribe(
    video_file_path: str,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    transcripts_dir: str = DEFAULT_TRANSCRIPTS_DIR,
    model_size: str = DEFAULT_MODEL_SIZE
) -> None:
    """Download audio from multiple videos and optionally transcribe them."""
    Path(output_dir).mkdir(exist_ok=True)
    Path(transcripts_dir).mkdir(exist_ok=True)
    urls, titles = extract_urls_from_file(video_file_path)
    print(f"Found {len(urls)} videos to download")
    print("-" * 50)
    successful_downloads = 0
    failed_downloads = 0
    for idx, (url, title) in enumerate(zip(urls, titles), 1):
        print(f"\n[{idx}/{len(urls)}] Processing: {title}")
        audio_file_path = str(Path(output_dir) / f"{title}.mp3")
        if Path(audio_file_path).exists():
            print(f"Audio file already exists: {title}.mp3")
        else:
            success = download_audio(url, output_dir, title)
            if success:
                successful_downloads += 1
            else:
                failed_downloads += 1
                continue
        transcript_file_path = str(Path(transcripts_dir) / f"{title}_transcript.txt")
        if not Path(transcript_file_path).exists():
            print(f"Transcribing: {title}...")
            transcript = transcribe_audio_whisper_local(audio_file_path, model_size)
            if transcript:
                with open(transcript_file_path, "w", encoding="utf-8") as f:
                    f.write(transcript)
                print(f"✓ Transcript saved: {title}_transcript.txt")
        else:
            print(f"Transcript already exists: {title}_transcript.txt")
        time.sleep(1)
    print("\n" + "=" * 50)
    print("Download Summary:")
    print(f"✓ Successful downloads: {successful_downloads}")
    print(f"✗ Failed downloads: {failed_downloads}")
    print(f"Total videos processed: {len(urls)}")
    print(f"Audio files saved in: {output_dir}")

def download_specific_categories(
    video_file_path: str,
    categories: Optional[List[str]] = None,
    output_dir: str = DEFAULT_OUTPUT_DIR
) -> None:
    """Download audio only from specific categories."""
    Path(output_dir).mkdir(exist_ok=True)
    with open(video_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    if categories is None:
        categories = DEFAULT_CATEGORIES
    for category in categories:
        print(f"\n--- Processing category: {category} ---")
        category_pattern = rf'{re.escape(category)}:(.*?)(?=\n\d+\.|$)'
        category_match = re.search(category_pattern, content, re.DOTALL)
        if not category_match:
            print(f"Category '{category}' not found")
            continue
        category_content = category_match.group(1)
        pattern = r'- (https://www\.youtube\.com/watch\?v=[^&\s]+).*?--> (.+)'
        matches = re.findall(pattern, category_content)
        for url, title in matches:
            clean_url = url.split('&list=')[0]
            clean_title = re.sub(r'[^\w\s-]', '', title.strip()).strip()
            clean_title = re.sub(r'[-\s]+', '_', clean_title)
            filename = f"{category.replace(' ', '_')}_{clean_title}"
            download_audio(clean_url, output_dir, filename)
            time.sleep(1)

def main():
    """Main entry point for the batch audio downloader CLI."""
    print("YouTube Audio Batch Downloader")
    print("=" * 40)
    print("1. Download all videos")
    print("2. Download specific categories")
    print("3. Download and transcribe all videos")
    video_file = DEFAULT_VIDEO_FILE
    choice = input("\nSelect option (1-3): ").strip()
    if choice == "1":
        batch_download_and_transcribe(video_file)
    elif choice == "2":
        print("\nAvailable categories:")
        for idx, cat in enumerate(DEFAULT_CATEGORIES, 1):
            print(f"{idx}. {cat}")
        selected = input("\nEnter category numbers (comma-separated, e.g., 1,3,5): ").strip()
        try:
            indices = [int(x.strip()) - 1 for x in selected.split(',')]
            selected_categories = [DEFAULT_CATEGORIES[i] for i in indices if 0 <= i < len(DEFAULT_CATEGORIES)]
            download_specific_categories(video_file, selected_categories)
        except ValueError:
            print("Invalid selection")
    elif choice == "3":
        print("This will download audio files and create transcripts (may take a while)...")
        confirm = input("Continue? (y/N): ").strip().lower()
        if confirm == 'y':
            batch_download_and_transcribe(video_file)
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main()
