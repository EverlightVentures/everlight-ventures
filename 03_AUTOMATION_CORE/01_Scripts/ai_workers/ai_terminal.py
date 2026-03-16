#!/usr/bin/env python3
"""
AI Terminal Tool - Call GPT from command line
Usage: ai "your question here"
"""

import sys
import os
from pathlib import Path

ENV_FILE = Path("/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/.env")

def load_env():
    """Load keys from .env file"""
    if ENV_FILE.exists():
        with open(ENV_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ.setdefault(key.strip(), value.strip())

def load_api_key():
    """Load OpenAI API key"""
    load_env()
    key = os.getenv('OPENAI_API_KEY')
    if not key:
        print("❌ No OPENAI_API_KEY found in .env or environment.")
        print(f"   Add it to: {ENV_FILE}")
        sys.exit(1)
    return key

def call_gpt(prompt, api_key):
    """Call OpenAI GPT API"""
    import requests

    url = "https://api.openai.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": "gpt-4",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        response.raise_for_status()

        result = response.json()
        return result['choices'][0]['message']['content']

    except requests.exceptions.RequestException as e:
        print(f"❌ API Error: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
        sys.exit(1)

def main():
    if len(sys.argv) < 2:
        print("Usage: ai \"your question here\"")
        print("\nExamples:")
        print("  ai \"What's the weather like?\"")
        print("  ai \"Write a Python function to parse CSV\"")
        print("  ai \"Explain quantum computing simply\"")
        sys.exit(1)

    prompt = ' '.join(sys.argv[1:])

    print("🤖 GPT is thinking...\n")

    api_key = load_api_key()
    response = call_gpt(prompt, api_key)

    print(response)
    print()

if __name__ == "__main__":
    main()
