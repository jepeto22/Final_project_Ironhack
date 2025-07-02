#!/usr/bin/env python3
"""
Test script for Rick Sanchez TTS endpoints
Make sure your Flask app is running on localhost:5000
"""

import requests
import json
import base64
import os
from datetime import datetime

BASE_URL = "http://localhost:5000"

def test_rick_tts_status():
    """Test Rick TTS configuration status."""
    print("🧪 Testing Rick TTS Status...")
    
    try:
        response = requests.get(f"{BASE_URL}/rick/tts/status")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Rick TTS Status Response:")
            print(json.dumps(data, indent=2))
            return data.get('available', False)
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing status: {e}")
        return False

def test_rick_tts_json():
    """Test Rick TTS with JSON response (base64 audio)."""
    print("\n🎵 Testing Rick TTS (JSON response)...")
    
    test_text = "Wubba lubba dub dub! Listen Morty, science is all about precision and understanding the universe!"
    
    try:
        response = requests.post(
            f"{BASE_URL}/rick/tts",
            json={"text": test_text},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Rick TTS JSON Response received!")
            print(f"📝 Original text: {data.get('original_text', 'N/A')}")
            print(f"🗣️ Processed text: {data.get('text', 'N/A')}")
            print(f"🎤 Voice ID: {data.get('voice_id', 'N/A')}")
            print(f"📦 Audio format: {data.get('audio_format', 'N/A')}")
            
            # Save audio if available
            if 'audio_base64' in data:
                audio_data = base64.b64decode(data['audio_base64'])
                filename = f"rick_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
                
                with open(filename, 'wb') as f:
                    f.write(audio_data)
                
                print(f"💾 Audio saved as: {filename}")
                print(f"📊 Audio size: {len(audio_data)} bytes")
                return True
            else:
                print("⚠️ No audio data in response")
                return False
                
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing JSON TTS: {e}")
        return False

def test_rick_tts_file():
    """Test Rick TTS with file download."""
    print("\n📁 Testing Rick TTS (File download)...")
    
    test_text = "Rick here! This is a test of the direct file download endpoint. Pretty cool, huh Morty?"
    
    try:
        response = requests.post(
            f"{BASE_URL}/rick/tts/file",
            json={"text": test_text},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            # Get filename from response headers or create one
            filename = response.headers.get('Content-Disposition', '').split('filename=')[-1].strip('"')
            if not filename:
                filename = f"rick_file_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
            
            with open(filename, 'wb') as f:
                f.write(response.content)
            
            print(f"✅ Rick TTS file downloaded!")
            print(f"💾 Saved as: {filename}")
            print(f"📊 File size: {len(response.content)} bytes")
            return True
            
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing file TTS: {e}")
        return False

def test_rick_with_science_question():
    """Test Rick TTS with a science-themed question."""
    print("\n🔬 Testing Rick TTS with Science Content...")
    
    # First get an answer from the RAG system
    science_question = "What happens inside a black hole?"
    
    try:
        # Get answer from RAG system
        rag_response = requests.post(
            f"{BASE_URL}/ask",
            json={
                "question": science_question,
                "mode": "crazy_scientist"  # Rick mode
            },
            headers={"Content-Type": "application/json"}
        )
        
        if rag_response.status_code == 200:
            rag_data = rag_response.json()
            answer = rag_data.get('answer', 'No answer available')
            print(f"🧠 RAG Answer: {answer[:100]}...")
            
            # Now convert to Rick TTS
            tts_response = requests.post(
                f"{BASE_URL}/rick/tts",
                json={"text": answer},
                headers={"Content-Type": "application/json"}
            )
            
            if tts_response.status_code == 200:
                tts_data = tts_response.json()
                
                # Save the Rick science explanation
                if 'audio_base64' in tts_data:
                    audio_data = base64.b64decode(tts_data['audio_base64'])
                    filename = f"rick_science_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp3"
                    
                    with open(filename, 'wb') as f:
                        f.write(audio_data)
                    
                    print(f"✅ Rick's science explanation saved as: {filename}")
                    print(f"🗣️ Rick says: {tts_data.get('text', 'N/A')[:150]}...")
                    return True
                
        print("❌ Could not complete science + TTS test")
        return False
        
    except Exception as e:
        print(f"❌ Error in science TTS test: {e}")
        return False

def main():
    """Run all Rick TTS tests."""
    print("🚀 Starting Rick Sanchez TTS Tests")
    print("=" * 50)
    
    # Test 1: Status check
    if not test_rick_tts_status():
        print("\n❌ Rick TTS is not available. Check your configuration!")
        print("💡 Make sure you have:")
        print("   - ElevenLabs API key in .env file")
        print("   - Custom Rick voice ID configured")
        print("   - Flask app running on localhost:5000")
        return
    
    # Test 2: JSON response
    test_rick_tts_json()
    
    # Test 3: File download
    test_rick_tts_file()
    
    # Test 4: Science content with Rick
    test_rick_with_science_question()
    
    print("\n" + "=" * 50)
    print("🎉 Rick TTS tests completed!")
    print("📁 Check the current directory for generated audio files")

if __name__ == "__main__":
    main()
