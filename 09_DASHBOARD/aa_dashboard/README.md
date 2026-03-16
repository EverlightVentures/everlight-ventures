# AA Dashboard

Local-first file dashboard with previews (images, video, audio, PDF, text, code), widgets, recent files, and a launchpad.

## Quick start

```bash
cd /mnt/sdcard/AA_MY_DRIVE/09_DASHBOARD/aa_dashboard
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open: http://localhost:8765

## Configure roots

Edit `config.json` to point at the folders you want indexed. Example:

```json
{
  "roots": ["/mnt/sdcard/AA_MY_DRIVE", "/mnt/sdcard/AA_MY_DRIVE/ProtonDrive"],
  "default_root": "/mnt/sdcard/AA_MY_DRIVE"
}
```

## Proton Drive sync (optional)

- `proton_sync.sh` runs a two-way sync between `ProtonDrive` (local) and `protondrive:AA_MY_DRIVE`.
- If it’s the first time, run `proton_sync_resync.sh` once to create the baseline, then use `proton_sync.sh`.

## Notes

- Search is substring-based and limited by `max_search_results`.
- Recent files are capped by `recent_limit` and skip `ignore_dirs`.
- File previews stream directly from disk.
