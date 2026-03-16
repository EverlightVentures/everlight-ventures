import os
import requests
import json

api_key = os.environ.get("OPENAI_API_KEY")

if not api_key:
    print("No API Key found.")
else:
    print(f"Testing key (prefix): {api_key[:10]}...")
    
    # Try a simple model list to check auth
    url = "https://api.openai.com/v1/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            print("Authentication Successful!")
            # Check if dalle-3 is in models
            models = [m['id'] for m in response.json()['data']]
            if 'dall-e-3' in models:
                print("DALL-E 3 is available.")
            else:
                print("DALL-E 3 NOT found in models list.")
        else:
            print(f"Authentication Failed. Status: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
