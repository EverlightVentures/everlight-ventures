import os
import sys
import requests
import json
import time

def send_to_n8n_canvas(file_path):
    # n8n Webhook URL (Assumed from typical local setup)
    # This should be updated to your actual n8n webhook URL
    N8N_WEBHOOK_URL = "http://localhost:5678/webhook/hive-log-to-canvas"
    
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        return

    with open(file_path, 'r') as f:
        content = f.read()

    filename = os.path.basename(file_path)
    
    # Payload for n8n
    payload = {
        "filename": filename,
        "content": content,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "source": "Hive Mind War Room",
        "doc_type": "War Log / Execution Report"
    }

    try:
        # We send the request to n8n which handles the Slack Canvas/Doc creation
        response = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"Successfully sent {filename} to n8n for Canvas generation.")
            return response.json()
        else:
            print(f"n8n Webhook returned status code {response.status_code}")
    except Exception as e:
        print(f"Failed to connect to n8n: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 log_to_canvas.py <path_to_markdown_log>")
    else:
        log_file = sys.argv[1]
        send_to_n8n_canvas(log_file)
