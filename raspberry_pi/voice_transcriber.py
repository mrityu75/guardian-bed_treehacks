#!/usr/bin/env python3
import os
import time
import subprocess
import requests
from openai import OpenAI

# Configuration
OPENAI_API_KEY = "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"
API_ENDPOINT = "http://172.30.202.252:8000/api/transcript"
AUDIO_DEVICE = "plughw:2,0"
CHUNK_DURATION = 5

client = OpenAI(api_key=OPENAI_API_KEY)

def record_audio(filename, duration=5):
    cmd = [
        'arecord',
        '-D', AUDIO_DEVICE,
        '-f', 'cd',
        '-d', str(duration),
        filename
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Recording failed: {e}")
        return False

def transcribe_audio(filename):
    try:
        with open(filename, 'rb') as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="en"
            )
        return transcript.text
    except Exception as e:
        print(f"Transcription failed: {e}")
        return None

def send_to_api(text):
    try:
        data = {
            'text': text,
            'timestamp': time.time(),
            'source': 'voice'
        }
        response = requests.post(API_ENDPOINT, json=data, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"API send failed: {e}")
        return False

def main():
    print("="*60)
    print("GUARDIAN BED - VOICE TRANSCRIPTION")
    print("="*60)
    print(f"Audio Device: {AUDIO_DEVICE}")
    print(f"Chunk Duration: {CHUNK_DURATION} seconds")
    print(f"API Endpoint: {API_ENDPOINT}")
    print("="*60)
    print("\nStarting continuous transcription...")
    print("Press Ctrl+C to stop\n")
    
    audio_file = "/tmp/audio_chunk.wav"
    count = 0
    
    try:
        while True:
            count += 1
            print(f"[{count}] Recording {CHUNK_DURATION} seconds...")
            
            if not record_audio(audio_file, CHUNK_DURATION):
                print("  ✗ Recording failed, retrying...")
                time.sleep(1)
                continue
            
            print(f"  ✓ Recorded. Transcribing...")
            
            text = transcribe_audio(audio_file)
            
            if text:
                print(f"  ✓ Transcript: \"{text}\"")
                
                if send_to_api(text):
                    print(f"  ✓ Sent to API")
                else:
                    print(f"  ✗ API send failed")
            else:
                print(f"  ✗ Transcription failed")
            
            print()
            
            if os.path.exists(audio_file):
                os.remove(audio_file)
                
    except KeyboardInterrupt:
        print("\n\nStopping transcription...")
        if os.path.exists(audio_file):
            os.remove(audio_file)
        print("Done!")

if __name__ == "__main__":
    main()
