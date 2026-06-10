# Google Docs Service Account Setup

**Date:** 2026-04-26
**Owner:** Marquise (only the Google Cloud Console steps need a human)
**Backend:** already patched. `gdocs_bridge.py` will pick up the JSON the second it lands at `/home/opc/secrets/google_service_account.json`.

## Why we are doing this

The current Google Docs path uses an installed-app user-OAuth refresh token (`/home/opc/secrets/google_docs_token.json`). Refresh tokens for "Testing" OAuth consent screens expire after 7 days, and Google has been silently rotating the secret on us. Every time it dies, every report from `broker-orch-full` and `wholesale-day` fails its Drive sync with `invalid_grant: Bad Request`, and the only fix is the user opening a browser to re-auth.

A **service account** is a non-human Google identity. Its JSON key never expires, never needs browser auth, and never sees a 7-day cap. It is the right tool for unattended server jobs.

## The 4 steps you need to do

> Total time: about 5 minutes. You only do this once, ever.

### 1. Open Google Cloud Console -> create / pick a project

- Go to https://console.cloud.google.com/iam-admin/serviceaccounts
- Sign in as the same Google account that owns your Drive folders.
- Top bar: pick a project (or click "New Project", name it `everlight-hive`, create, then pick it).

### 2. Create a Service Account

- Click **"+ Create Service Account"**.
- **Service account name:** `everlight-gdocs-publisher`
- **Service account ID:** auto-fills (looks like `everlight-gdocs-publisher@everlight-hive.iam.gserviceaccount.com`). Copy this email -- you will need it in step 4.
- Click **Create and Continue**, skip the optional role/grant screens (click **Continue** then **Done**).

### 3. Generate a JSON key + drop it on Oracle

- Click into the new service account row.
- Tab **Keys** -> **Add Key** -> **Create new key** -> **JSON** -> **Create**.
- Browser downloads `everlight-hive-xxxxx.json`. **This is the only copy.** Google does not store it.
- Upload it to Oracle:

```bash
scp -i /root/.ssh/oracle_key.pem ~/Downloads/everlight-hive-*.json \
    opc@163.192.19.196:/home/opc/secrets/google_service_account.json
ssh -i /root/.ssh/oracle_key.pem opc@163.192.19.196 \
    "chmod 600 /home/opc/secrets/google_service_account.json"
```

### 4. Enable APIs + share the Drive folder with the SA email

**4a. Enable Google Docs API and Drive API on the project** (one click each):
- https://console.cloud.google.com/apis/library/docs.googleapis.com -> **Enable**
- https://console.cloud.google.com/apis/library/drive.googleapis.com -> **Enable**

**4b. Share your "Hive" Drive folder with the service account email.**
- Open Google Drive in a browser.
- Find the parent folder you publish reports under (the one mapped to `GOOGLE_DOCS_ROOT_FOLDER_ID`, or just the top-level folder you have been writing to). If you do not have one yet, make `Hive` at Drive root.
- Right-click -> **Share** -> paste the SA email from step 2 (e.g. `everlight-gdocs-publisher@everlight-hive.iam.gserviceaccount.com`) -> set role **Editor** -> uncheck "Notify people" -> **Share**.

Why this matters: the SA scope is `drive.file`, which only sees files **the SA created or files explicitly shared with it**. If we skip the share, the SA can still create new Docs but cannot file them under your existing folder tree -- they will land at the SA's own Drive root, invisible to you.

## What happens after step 4

The next time any report fires (broker-orch-full, wholesale-day, hive_3format, etc.) the patched `gdocs_bridge.py` automatically:

1. Sees `/home/opc/secrets/google_service_account.json` exists.
2. Mints a fresh access token from it (no refresh-token rot, never expires).
3. Creates the Doc, files it under the shared folder, returns the Drive URL.
4. The success log line shows `"auth": "service_account"` so you know the new path is active.

If the SA file is ever missing or invalid, the code silently falls through to the old user-OAuth path, so this is a strict upgrade -- nothing breaks.

## Smoke test you can run after upload

```bash
ssh -i /root/.ssh/oracle_key.pem opc@163.192.19.196 \
    "python3 /tmp/test_publish.py"
```

Expected: a JSON blob with `"ok": true` and a real `https://docs.google.com/document/d/.../edit` link. Open it; the test doc should sit inside `Hive/SmokeTests/` under the folder you shared.

## What is already done (no action required)

- `gdocs_bridge.py` patched (commit-pending) with `_load_service_account_access_token()` and SA-first auth path. Backup at `/home/opc/content_tools/gdocs_bridge.py.bak.20260426_101210`.
- Library `google.oauth2.service_account` already installed in the system Python.
- Smoke-test script staged at `/tmp/test_publish.py` on Oracle.
- Existing user-OAuth path preserved as fallback so nothing breaks during the upload window.

## Optional cleanup (after the SA path is verified)

- Delete `/home/opc/secrets/google_docs_token.json` and `/home/opc/secrets/google_client_secret.json`.
- Delete `/home/opc/reauth_google_docs.py`.
- Remove the "run reauth_google_docs.py" line from `CLAUDE.md` and the most-recent MEMORY.md entry.

Backend Hand.
