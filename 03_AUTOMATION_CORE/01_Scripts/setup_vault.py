#!/usr/bin/env python3
"""
Credential Vault Setup Script
Migrates all plaintext credentials into encrypted GPG vault
"""

import os
import json
import subprocess
import shutil
from pathlib import Path
from getpass import getpass

# Base directory
BASE_DIR = Path("/mnt/sdcard/AA_MY_DRIVE")
VAULT_DIR = BASE_DIR / "03_AUTOMATION_CORE/03_Credentials"
BACKUP_DIR = BASE_DIR / "08_BACKUPS/Credentials_Plaintext_Backup"

# Known credential files (from security audit)
CREDENTIAL_FILES = {
    "gpt_api_key": "A_Rich/A_Projects/C_My_Docs/ZZ_Rich/Y_My_Inventory_Bag/Personal_Documents/Text_Files/Api_Keys/gpt_passkey.md",
    "phantom_seed": "A_Rich/A_Projects/C_My_Docs/ZZ_Rich/Y_Accounts/Phantom/seed_phrase_phantom.py",
    "pos_env": "A_Rich/A_Projects/A_Everlight_Ventures/Mountain Gardens Nursery POS/Mountain Gardens Nursery POS (working_beta) (copy).bak/.env",
    "google_oauth": "A_Rich/C_Downloads/client_secret_864189495801-pssn6fg438ahieth9vqih41a188smghu.apps.googleusercontent.com.json",
}

def read_env_file(filepath):
    """Parse .env file into dict"""
    env_vars = {}
    if not filepath.exists():
        return env_vars

    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip().strip('"').strip("'")
    return env_vars

def collect_credentials():
    """Collect all credentials into structured dict"""
    print("🔍 Collecting credentials from files...")

    credentials = {
        "api_keys": {},
        "crypto": {},
        "databases": {},
        "oauth": {},
        "services": {}
    }

    # GPT API Key
    gpt_file = BASE_DIR / CREDENTIAL_FILES["gpt_api_key"]
    if gpt_file.exists():
        with open(gpt_file, 'r') as f:
            content = f.read().strip()
            credentials["api_keys"]["gpt"] = content
        print(f"  ✓ Found GPT API key")

    # Phantom Seed Phrase (CRITICAL)
    phantom_file = BASE_DIR / CREDENTIAL_FILES["phantom_seed"]
    if phantom_file.exists():
        with open(phantom_file, 'r') as f:
            content = f.read().strip()
            # Extract seed phrase from Python file
            if 'seed_phrase' in content or 'SEED' in content:
                credentials["crypto"]["phantom_seed"] = content
        print(f"  ✓ Found Phantom seed phrase")

    # POS .env file
    env_file = BASE_DIR / CREDENTIAL_FILES["pos_env"]
    if env_file.exists():
        env_vars = read_env_file(env_file)
        credentials["databases"]["pos_system"] = env_vars
        print(f"  ✓ Found POS credentials ({len(env_vars)} keys)")

    # Google OAuth
    oauth_file = BASE_DIR / CREDENTIAL_FILES["google_oauth"]
    if oauth_file.exists():
        with open(oauth_file, 'r') as f:
            oauth_data = json.load(f)
            credentials["oauth"]["google"] = oauth_data
        print(f"  ✓ Found Google OAuth credentials")

    # Proton Drive (from rclone config)
    print(f"  ℹ️  Proton Drive credentials stored in rclone config (already encrypted)")

    return credentials

def backup_plaintext(credentials):
    """Backup plaintext files before deletion"""
    print(f"\n📦 Creating plaintext backup in {BACKUP_DIR}...")

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    for category, files in CREDENTIAL_FILES.items():
        src = BASE_DIR / files
        if src.exists():
            dst = BACKUP_DIR / src.name
            shutil.copy2(src, dst)
            print(f"  ✓ Backed up {src.name}")

    print(f"  ✓ Backup complete: {BACKUP_DIR}")

def encrypt_vault(credentials, passphrase):
    """Encrypt credentials with GPG"""
    print("\n🔐 Encrypting vault with GPG (AES256)...")

    # Write credentials to temp JSON
    temp_json = VAULT_DIR / "credentials.json"
    with open(temp_json, 'w') as f:
        json.dump(credentials, f, indent=2)

    # Encrypt with GPG
    encrypted_file = VAULT_DIR / "credentials.json.gpg"

    # Use passphrase from stdin
    process = subprocess.Popen(
        ['gpg', '--symmetric', '--cipher-algo', 'AES256', '--batch',
         '--passphrase-fd', '0', '--output', str(encrypted_file), str(temp_json)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    stdout, stderr = process.communicate(input=passphrase.encode())

    if process.returncode != 0:
        print(f"  ❌ Encryption failed: {stderr.decode()}")
        return False

    # Delete plaintext JSON
    temp_json.unlink()
    print(f"  ✓ Encrypted vault created: {encrypted_file}")

    return True

def delete_plaintext_files(dry_run=False):
    """Delete original plaintext credential files"""
    print("\n🗑️  Deleting plaintext credential files...")

    for category, files in CREDENTIAL_FILES.items():
        src = BASE_DIR / files
        if src.exists():
            if dry_run:
                print(f"  [DRY RUN] Would delete: {src}")
            else:
                src.unlink()
                print(f"  ✓ Deleted: {src}")

def test_decrypt(passphrase):
    """Test that vault can be decrypted"""
    print("\n🧪 Testing decryption...")

    encrypted_file = VAULT_DIR / "credentials.json.gpg"

    process = subprocess.Popen(
        ['gpg', '--decrypt', '--quiet', '--batch', '--passphrase-fd', '0', str(encrypted_file)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    stdout, stderr = process.communicate(input=passphrase.encode())

    if process.returncode != 0:
        print(f"  ❌ Decryption test failed!")
        return False

    try:
        creds = json.loads(stdout.decode())
        print(f"  ✓ Decryption successful")
        print(f"  ✓ Found {len(creds)} credential categories")
        return True
    except:
        print(f"  ❌ Failed to parse decrypted JSON")
        return False

def main():
    print("=" * 60)
    print("  EVERLIGHT CREDENTIAL VAULT SETUP")
    print("=" * 60)

    # Collect credentials
    credentials = collect_credentials()

    if not any(credentials.values()):
        print("\n❌ No credentials found. Nothing to encrypt.")
        return

    print(f"\n📊 Summary:")
    print(f"  - API Keys: {len(credentials['api_keys'])}")
    print(f"  - Crypto: {len(credentials['crypto'])}")
    print(f"  - Databases: {len(credentials['databases'])}")
    print(f"  - OAuth: {len(credentials['oauth'])}")

    # Confirm
    print(f"\n⚠️  This will:")
    print(f"  1. Backup plaintext files to {BACKUP_DIR}")
    print(f"  2. Encrypt credentials with GPG (AES256)")
    print(f"  3. Delete plaintext credential files")

    response = input("\nContinue? (yes/no): ").strip().lower()
    if response != 'yes':
        print("❌ Aborted.")
        return

    # Get passphrase
    print("\n🔑 Enter encryption passphrase (store in password manager!):")
    passphrase = getpass("Passphrase: ")
    passphrase_confirm = getpass("Confirm: ")

    if passphrase != passphrase_confirm:
        print("❌ Passphrases don't match. Aborted.")
        return

    if len(passphrase) < 12:
        print("❌ Passphrase too short (minimum 12 characters). Aborted.")
        return

    # Backup plaintext
    backup_plaintext(credentials)

    # Encrypt
    if not encrypt_vault(credentials, passphrase):
        print("❌ Encryption failed. Plaintext files NOT deleted.")
        return

    # Test decryption
    if not test_decrypt(passphrase):
        print("❌ Decryption test failed. Plaintext files NOT deleted.")
        return

    # Delete plaintext (ask again for safety)
    print("\n⚠️  FINAL CONFIRMATION")
    print(f"Vault encrypted successfully. Delete plaintext files now?")
    response = input("Type 'DELETE' to confirm: ").strip()

    if response == 'DELETE':
        delete_plaintext_files(dry_run=False)
        print("\n✅ VAULT SETUP COMPLETE")
        print(f"\n📍 Encrypted vault: {VAULT_DIR / 'credentials.json.gpg'}")
        print(f"📍 Plaintext backup: {BACKUP_DIR}")
        print(f"\n⚠️  IMPORTANT:")
        print(f"  - Store passphrase in password manager")
        print(f"  - Backup encrypted vault to Proton Drive")
        print(f"  - Test vault access: gpg --decrypt {VAULT_DIR / 'credentials.json.gpg'}")
    else:
        print("\n⚠️  Plaintext files NOT deleted (manual deletion required)")
        print(f"   Encrypted vault ready at: {VAULT_DIR / 'credentials.json.gpg'}")

if __name__ == "__main__":
    main()
