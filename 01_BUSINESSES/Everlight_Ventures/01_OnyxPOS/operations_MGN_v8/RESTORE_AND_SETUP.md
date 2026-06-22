# Mountain Gardens Nursery POS -- Restore & Setup (Dell Latitude)

This is the **original Mountain Gardens Nursery POS** (Flask app). It is NOT the Onyx
SaaS conversion -- ignore the `onyx_pos/` and `api_v2_may2026/` folders for this restore.

- **What runs:** `MGN_APP.py` (Flask) + `POS_CORE.py` (engine). Port 5000.
- **Owner login (already in the data):** Employee ID `1001`, PIN `8008`.
- **GitHub branch with the hardened code:** `mgn-pos-restore`.

---

## 1. Get the code onto the Dell

The POS lives inside the Everlight monorepo. Pull ONLY this app (not the 1.9 GB of repo history):

```bash
mkdir -p ~/mgn && cd ~/mgn
git clone --filter=blob:none --no-checkout git@github.com:EverlightVentures/everlight-ventures.git
cd everlight-ventures
git sparse-checkout init --cone
git sparse-checkout set "01_BUSINESSES/Everlight_Ventures/01_OnyxPOS/operations_MGN_v8"
git checkout mgn-pos-restore
cd "01_BUSINESSES/Everlight_Ventures/01_OnyxPOS/operations_MGN_v8"
```

(No GitHub access on the Dell? Use HTTPS + a Personal Access Token, or rsync the folder over
Tailscale from another Everlight machine -- see `../../../../../06_DEVELOPMENT/everlight_os/docs/ONYX_POS_RESTORE.md`.)

## 2. Install (Python 3.9+ required)

```bash
sudo apt install -y python3 python3-venv python3-pip   # if needed
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

## 3. (Optional) secrets -- create `.env`

None are required to boot. Add only what you want active:

```bash
cat > .env <<'EOF'
SECRET_KEY=change-me-to-a-random-string
# End-of-day email (see INTEGRITY_AND_ROADMAP.md -- the send code is a planned step):
MGN_EOD_EMAIL=1m.rich.gee@gmail.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=you@gmail.com
SMTP_PASS=your-gmail-app-password
SMTP_FROM=you@gmail.com
EOF
```

## 4. Run

```bash
./START_POS.sh start     # start  (also: stop | restart | status | logs)
#   START_POS.sh is now portable -- it auto-detects this folder, no path editing needed.
# or, simplest:
python MGN_APP.py        # serves on 127.0.0.1:5000
```

Open **http://127.0.0.1:5000** and log in as `1001` / `8008`.
To reach it from other devices on the shop LAN: `HOST=0.0.0.0 ./START_POS.sh start`.

## 5. Verify it's healthy

```bash
# Ring a $0 test sale in the UI, then confirm it persisted:
ls -R Sales_Logs/ | tail
# Run the integrity tests:
cd tools && python3 -m unittest test_pos_core_integrity test_inventory_transfer -v
```

## Desktop icon (optional)
Edit `MountainGardensPOS.desktop` -- set `Path=` and `Exec=` to this folder -- then copy it to
`~/.local/share/applications/`.

---

## What changed in this restore (so you're not surprised)
- `START_POS.sh` is now **portable** (no hardcoded `/home/mgn/...` path).
- App binds **127.0.0.1** by default (was `0.0.0.0`). Use `HOST=0.0.0.0` for LAN.
- Sales logging was **hardened** (see `INTEGRITY_AND_ROADMAP.md`): failed writes now fail loud,
  inventory writes are atomic + locked, daily-revenue math fixed. Your data files are untouched.
- New `tools/inventory_transfer.py` converts inventory CSV to/from Square, Shopify, QuickBooks.
- **Product search now works.** The catalog was un-searchable (the tenant pointed at a dead path,
  and every item was named "Plant"). Fixed, and the repaired `Items.csv` ships in this branch --
  search "5 gal" and products appear. Real names need an owner re-import later (current labels are a
  searchable stopgap built from Size + price).
- **Quick-add at the register.** A failed search shows a **"+ Quick Add"** button -- enter name +
  price and it drops straight into the cart (creates a `QA-` item). Managers reconcile these to real
  products at **`/inventory/reconcile`**.
- **End of day exports files.** Close-out saves the day's Sales + Summary + Closeout CSVs to
  `Daily_Reports/<date>/` and emails them. Set `MGN_EOD_EMAIL=you@...,adam@...` (comma-separated) +
  `SMTP_*` in `.env` for the multi-recipient send (local saves happen regardless).
