import requests
import json

# Test with existing audio to save ElevenLabs credits
API_URL = "http://localhost:8000"
GAMEPLAY_VIDEO = "/Users/naman/Downloads/videoplayback.mp4"
EXISTING_AUDIO = "/Users/naman/Downloads/clip_app2/clip_app_2/outputs/job_20251120_001334/generated_audio.mp3"

def test_with_existing_audio():
    """Test transcription and video processing with existing ElevenLabs audio"""
    print("Make sure uvicorn is running on port 8000")
    print(f"Testing pipeline with existing audio file...")
    
    # We'll need to create a custom endpoint or test transcriber directly
    # For now, let's just test the full pipeline with the script
    SCRIPT = "This is a test of the automated video generation system. We are creating a short video from this text."
    
    payload = {
        "script": SCRIPT,
        "voice_provider": "elevenlabs",
        "voice_id": "JBFqnCBsd6RMkjVDRZzb",
        "gameplay_video_path": GAMEPLAY_VIDEO
    }
    
    try:
        response = requests.post(f"{API_URL}/process_script", json=payload)
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✅ SUCCESS!")
            print(f"Job ID: {result['job_id']}")
            print(f"Status: {result['status']}")
            print(f"Output URL: {result['output_url']}")
        else:
            print(f"\n❌ Test failed: {response.status_code} {response.reason}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError as e:
        print(f"Test failed: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
        
if __name__ == "__main__":
    test_with_existing_audio()
