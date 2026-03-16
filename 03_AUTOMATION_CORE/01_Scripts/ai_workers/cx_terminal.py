#!/usr/bin/env python3
"""
Codex Terminal Tool - Code-focused GPT from command line
Usage: cx "write a function to parse JSON"
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

def call_codex(prompt, api_key):
    """Call OpenAI GPT API with code-focused system prompt"""
    import requests

    url = "https://api.openai.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    system_prompt = """You are Codex, an expert programming assistant.
You write clean, efficient, well-documented code.
- Always provide working code examples
- Include brief comments explaining complex logic
- Suggest best practices when relevant
- Be concise but thorough
- Default to Python unless another language is specified"""

    data = {
        "model": "gpt-4",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 2000
    }

    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
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
        print("Usage: cx \"your coding request here\"")
        print("\nExamples:")
        print("  cx \"write a function to parse CSV files\"")
        print("  cx \"create a Flask API endpoint for user login\"")
        print("  cx \"fix this error: TypeError: cannot unpack non-iterable\"")
        print("  cx \"optimize this SQL query: SELECT * FROM users\"")
        sys.exit(1)

    prompt = ' '.join(sys.argv[1:])

    print("💻 Codex is coding...\n")

    api_key = load_api_key()
    response = call_codex(prompt, api_key)

    print(response)
    print()

if __name__ == "__main__":
    main()
