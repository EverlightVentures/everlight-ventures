import os
import datetime

def generate_tree(startpath, exclude_dirs):
    tree_lines = []
    for root, dirs, files in os.walk(startpath):
        dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith('.')]
        level = root.replace(startpath, '').count(os.sep)
        if level > 2: continue # Limit depth for tree visualization
        indent = '│   ' * (level - 1) + '├── ' if level > 0 else ''
        tree_lines.append(f"{indent}{os.path.basename(root)}/")
    return "\n".join(tree_lines)

def generate_mermaid(startpath, exclude_dirs):
    mermaid_lines = ["mindmap", "  root((AA_MY_DRIVE))"]
    # Only map the top-level 01-09 folders for the mindmap to keep it readable
    items = sorted([d for d in os.listdir(startpath) if os.path.isdir(os.path.join(startpath, d))])
    for item in items:
        if item not in exclude_dirs and not item.startswith('.') and item[0:2].isdigit():
            mermaid_lines.append(f"    {item}")
            # Add sub-subfolders for the mindmap
            subpath = os.path.join(startpath, item)
            subitems = sorted([sd for sd in os.listdir(subpath) if os.path.isdir(os.path.join(subpath, sd))])
            for subitem in subitems:
                if not subitem.startswith('.') and not subitem.startswith('_'):
                    mermaid_lines.append(f"      {subitem}")
    return "\n".join(mermaid_lines)

import requests

def notify_slack_manifest(timestamp):
    # This URL should be your Slack Webhook for #05-system-alerts
    SLACK_WEBHOOK_URL = "http://localhost:5678/webhook/slack-system-alerts"
    payload = {
        "text": f"🗺️ *Workspace Manifest Updated*\n*Timestamp:* {timestamp}\n*Changes:* File tree synchronized with 01-09 structure.\n📄 <https://github.com/your-repo/WORKSPACE_MANIFEST.md|View Manifest>"
    }
    try:
        requests.post(SLACK_WEBHOOK_URL, json=payload)
    except:
        pass

def update_manifest():
    root_path = "/mnt/sdcard/AA_MY_DRIVE"
    manifest_path = os.path.join(root_path, "WORKSPACE_MANIFEST.md")
    exclude = ['_logs', '.git', '.claude', '.gemini', 'plans', '.aa_dashboard_cache', '.nvim', '.system', '.perplexity', '.codex']
    
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tree = generate_tree(root_path, exclude)
    mermaid = generate_mermaid(root_path, exclude)

    # ... [content generation logic] ...

    with open(manifest_path, 'w') as f:
        f.write(content)
    print(f"Manifest updated at {timestamp}")
    notify_slack_manifest(timestamp)

if __name__ == "__main__":
    update_manifest()
