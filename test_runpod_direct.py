import requests
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Test RunPod Chatterbox API directly
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
RUNPOD_ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID", "4fb7cwijyp7xge")

if not RUNPOD_API_KEY:
    print("❌ Error: RUNPOD_API_KEY not found in environment variables")
    print("Please set RUNPOD_API_KEY in your .env file")
    exit(1)

url = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/run"
headers = {
    "Authorization": f"Bearer {RUNPOD_API_KEY}",
    "Content-Type": "application/json"
}
payload = {
    "input": {
        "text": "Hello, this is a test.",
        "voice_mode": "predefined",
        "output_format": "wav"
    }
}

print(f"Testing RunPod API: {url}")
print(f"Using API key from environment: {RUNPOD_API_KEY[:10]}...{RUNPOD_API_KEY[-4:]}")
print(f"Headers: {json.dumps({k: '***REDACTED***' if k == 'Authorization' else v for k, v in headers.items()}, indent=2)}")
print(f"Payload: {json.dumps(payload, indent=2)}")
print("\nSending request...")

response = requests.post(url, json=payload, headers=headers, timeout=30)

print(f"\nStatus Code: {response.status_code}")
print(f"Response: {response.text}")

if response.status_code == 200:
    result = response.json()
    print(f"\nJob ID: {result.get('id')}")
    print("✅ API call successful!")
else:
    print(f"❌ API call failed: {response.status_code}")
