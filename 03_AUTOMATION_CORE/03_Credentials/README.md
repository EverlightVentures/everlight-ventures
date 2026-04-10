# ENCRYPTED CREDENTIAL VAULT

**⚠️ SECURITY CRITICAL - DO NOT COMMIT TO GIT**

This directory contains all sensitive credentials encrypted with GPG (AES256).

## Stored Credentials

- API keys (GPT, Claude, Perplexity, etc.)
- OAuth tokens (Google, Meta, TikTok, Discord)
- Database passwords
- Cryptocurrency seed phrases
- POS system credentials
- Proton Drive credentials
- Payment processor keys (Stripe, Coinbase Commerce)

## Usage

### Encrypt credentials
```bash
gpg --symmetric --cipher-algo AES256 credentials.json
# Creates: credentials.json.gpg
rm credentials.json  # Delete plaintext
```

### Decrypt credentials
```bash
gpg --decrypt credentials.json.gpg > credentials.json
# Use in script, then delete
```

### In Python scripts
```python
import subprocess
import json

def load_credentials():
    result = subprocess.run(
        ['gpg', '--decrypt', '--quiet', '03_AUTOMATION_CORE/03_Credentials/credentials.json.gpg'],
        capture_output=True,
        text=True
    )
    return json.loads(result.stdout)

creds = load_credentials()
api_key = creds['gpt']['api_key']
```

## Setup First Time

Run: `python3 03_AUTOMATION_CORE/01_Scripts/setup_vault.py`

This will:
1. Collect all existing credentials
2. Create master credentials.json
3. Encrypt with GPG
4. Delete plaintext versions
5. Update scripts to use vault

## Backup

Encrypted vault is synced to Proton Drive.
Keep passphrase in password manager (NOT on device).
