#!/usr/bin/env python3
"""
Google Drive Folder Tree Setup -- One-time script.

Creates the Everlight Ventures folder structure in Google Drive
as defined in google_drive_structure.md.

Requires: google-api-python-client, google-auth-oauthlib
Install: pip install google-api-python-client google-auth-oauthlib

Two auth modes:
  1. Service Account (headless): Set GOOGLE_APPLICATION_CREDENTIALS env var
  2. OAuth (interactive): Uses client_secret JSON file

Usage:
    python3 gdrive_setup.py                    # Create folder tree
    python3 gdrive_setup.py --list             # List existing folders
    python3 gdrive_setup.py --dry-run          # Preview without creating
    python3 gdrive_setup.py --export-ids       # Export folder ID mapping
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path

log = logging.getLogger("gdrive_setup")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Folder tree definition (matches google_drive_structure.md)
FOLDER_TREE = {
    "Everlight Ventures": {
        "00_Command_Center": {
            "Daily_Briefings": {},
            "War_Room": {},
            "Meeting_Notes": {},
            "System_Status": {},
        },
        "01_Broker_OS": {
            "Scout_Reports": {},
            "Match_Reports": {},
            "Outreach_Logs": {},
            "Seller_Replies": {},
            "Deal_Pipeline": {},
            "Daily_KPI": {},
            "Follow_Up_Tracker": {},
        },
        "02_XLM_Bot": {
            "Trade_Reports": {},
            "Strategy_Analysis": {},
            "Risk_Alerts": {},
            "Daily_Scoreboard": {},
            "AI_Advisor_Decisions": {},
        },
        "03_Content_Factory": {
            "Social_Posts": {},
            "Avatar_Output": {},
            "Funnel_Reports": {},
            "SEO_Reports": {},
            "Publishing_Pipeline": {},
        },
        "04_Revenue_Dashboard": {
            "Stripe_Reports": {},
            "Monthly_Revenue": {},
            "Product_Performance": {},
            "Affiliate_Reports": {},
        },
        "05_AI_Workers": {
            "Hive_Mind_Logs": {},
            "Task_Handoff": {},
            "Blinko_Knowledge": {},
            "Agent_Performance": {},
        },
        "06_Infrastructure": {
            "Oracle_Cloud": {},
            "N8N_Workflow_Logs": {},
            "Langfuse_Reports": {},
            "Netdata_Snapshots": {},
            "Metabase_Exports": {},
        },
        "07_Logistics": {
            "Client_Files": {},
            "Invoices": {},
            "Service_Reports": {},
        },
        "08_Legal_Compliance": {
            "Contracts": {},
            "Terms_Privacy": {},
            "Compliance_Audits": {},
        },
        "09_Archives": {
            "2025": {},
            "2026": {},
        },
    }
}

# Where to save the folder ID mapping
ID_MAP_PATH = Path(__file__).parent / "gdrive_folder_ids.json"


def _get_drive_service():
    """Authenticate and return Google Drive API service."""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        # Try service account first
        creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if creds_path and Path(creds_path).exists():
            creds = service_account.Credentials.from_service_account_file(
                creds_path,
                scopes=["https://www.googleapis.com/auth/drive"]
            )
            return build("drive", "v3", credentials=creds)
    except ImportError:
        pass

    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        SCOPES = ["https://www.googleapis.com/auth/drive"]
        token_path = Path(__file__).parent / "gdrive_token.json"

        creds = None
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # Look for client secret file
                client_secrets = [
                    Path("/mnt/sdcard/Download") / f
                    for f in os.listdir("/mnt/sdcard/Download")
                    if f.startswith("client_secret_") and f.endswith(".json")
                ]
                if not client_secrets:
                    log.error("No Google OAuth client secret found in /mnt/sdcard/Download/")
                    log.error("Download one from console.cloud.google.com -> APIs -> Credentials")
                    return None
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(client_secrets[0]), SCOPES
                )
                creds = flow.run_local_server(port=0)
            token_path.write_text(creds.to_json())

        return build("drive", "v3", credentials=creds)
    except ImportError:
        log.error("Install required: pip install google-api-python-client google-auth-oauthlib")
        return None
    except Exception as e:
        log.error(f"Auth failed: {e}")
        return None


def _find_existing_folder(service, name, parent_id=None):
    """Check if a folder already exists."""
    query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"

    results = service.files().list(
        q=query,
        spaces="drive",
        fields="files(id, name)",
        pageSize=5,
    ).execute()

    files = results.get("files", [])
    return files[0]["id"] if files else None


def _create_folder(service, name, parent_id=None, dry_run=False):
    """Create a folder in Google Drive. Returns folder ID."""
    # Check if it already exists
    existing = _find_existing_folder(service, name, parent_id)
    if existing:
        log.info(f"  EXISTS: {name} ({existing})")
        return existing

    if dry_run:
        log.info(f"  [DRY RUN] Would create: {name}")
        return f"dry_run_{name}"

    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        metadata["parents"] = [parent_id]

    folder = service.files().create(
        body=metadata,
        fields="id"
    ).execute()

    folder_id = folder.get("id")
    log.info(f"  CREATED: {name} ({folder_id})")
    return folder_id


def _create_tree(service, tree, parent_id=None, path="", id_map=None, dry_run=False):
    """Recursively create folder tree."""
    if id_map is None:
        id_map = {}

    for name, children in tree.items():
        current_path = f"{path}/{name}" if path else name
        folder_id = _create_folder(service, name, parent_id, dry_run)
        id_map[current_path] = folder_id

        if children:
            _create_tree(service, children, folder_id, current_path, id_map, dry_run)

    return id_map


def create_folder_tree(dry_run=False):
    """Main: create the entire Google Drive folder tree."""
    service = _get_drive_service()
    if not service:
        log.error("Could not authenticate with Google Drive")
        return None

    log.info("Creating Everlight Ventures Google Drive folder tree...")
    id_map = _create_tree(service, FOLDER_TREE, dry_run=dry_run)

    # Save ID mapping
    if not dry_run and id_map:
        ID_MAP_PATH.write_text(json.dumps(id_map, indent=2))
        log.info(f"Folder ID mapping saved to: {ID_MAP_PATH}")

        # Also generate the n8n folder map update
        _generate_n8n_map(id_map)

    return id_map


def _generate_n8n_map(id_map):
    """Generate the folder map for the n8n workflow Code node."""
    # Map the folder paths used in gdocs_bridge.py to their Drive IDs
    bridge_map = {}
    for full_path, folder_id in id_map.items():
        # Strip "Everlight Ventures/" prefix
        short = full_path.replace("Everlight Ventures/", "", 1)
        bridge_map[short] = folder_id

    n8n_map_path = Path(__file__).parent / "gdrive_n8n_folder_map.json"
    n8n_map_path.write_text(json.dumps(bridge_map, indent=2))
    log.info(f"n8n folder map saved to: {n8n_map_path}")
    log.info("Update the 'Resolve Folder' Code node in n8n with these IDs.")


def list_folders():
    """List existing top-level folders in Drive."""
    service = _get_drive_service()
    if not service:
        return

    results = service.files().list(
        q="mimeType='application/vnd.google-apps.folder' and trashed=false and 'root' in parents",
        spaces="drive",
        fields="files(id, name, createdTime)",
        orderBy="name",
        pageSize=50,
    ).execute()

    for f in results.get("files", []):
        print(f"  {f['name']} ({f['id']}) -- {f.get('createdTime', '?')}")


def export_ids():
    """Export current folder ID mapping."""
    if ID_MAP_PATH.exists():
        data = json.loads(ID_MAP_PATH.read_text())
        for path, fid in sorted(data.items()):
            print(f"  {path}: {fid}")
    else:
        log.info("No folder ID mapping found. Run setup first.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Google Drive folder tree setup")
    parser.add_argument("--dry-run", action="store_true", help="Preview without creating")
    parser.add_argument("--list", action="store_true", help="List existing top-level folders")
    parser.add_argument("--export-ids", action="store_true", help="Export folder ID mapping")
    args = parser.parse_args()

    if args.list:
        list_folders()
    elif args.export_ids:
        export_ids()
    else:
        result = create_folder_tree(dry_run=args.dry_run)
        if result:
            total = len(result)
            print(f"\n{'[DRY RUN] Would create' if args.dry_run else 'Created'} {total} folders.")
            print(f"Next steps:")
            print(f"  1. Run: python3 gdrive_setup.py (without --dry-run) to create folders")
            print(f"  2. Copy folder IDs from gdrive_n8n_folder_map.json into n8n 'Resolve Folder' node")
            print(f"  3. Share root 'Everlight Ventures' folder with your team")
