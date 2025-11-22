import requests
import json

# Test RunPod Chatterbox API directly
url = "https://api.runpod.ai/v2/4fb7cwijyp7xge/run"
headers = {
    "Authorization": "Bearer rpa_MBB20AN2T8P8AFLINDQH9PB8XBXVB5KUVT0DQ99J12yoxr",
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
print(f"Headers: {json.dumps({k: v[:20] + '...' if k == 'Authorization' else v for k, v in headers.items()}, indent=2)}")
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
