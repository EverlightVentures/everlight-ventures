# Mountain Gardens POS -- Nursery Deploy Runbook

The till that never loses a sale. This is the one page that gets the POS running on
the Dell laptop today and on the nursery mini-PC later, with every feature you have
on one machine showing up identically on the next.

Nothing here is hard. The launcher does the heavy lifting. You mostly copy two
commands and open a browser.

---

## 1. What you are setting up

- **One central machine** (the mini-PC at the nursery, or the Dell for now) runs the
  POS. All the files -- sales, customers, inventory, payroll, backups -- live ONLY on
  that machine.
- **Staff phones** are just screens. They open the POS in a web browser over the shop
  WiFi. They save nothing locally. Every sale they ring up is written to the central
  machine. One brain, many screens.
- **GitHub is the master.** Every machine pulls the same code from GitHub, so the Dell
  and the nursery PC are always feature-for-feature identical. You never copy files by
  hand.

---

## 2. First-time install (about 5 minutes)

You need: the machine on, internet for the first install, and Python 3 (already on any
Mac/Linux; on Windows install from python.org and tick "Add to PATH").

**Step 1 -- get the code.**

```
git clone git@github.com:EverlightVentures/everlight-ventures.git everlight
cd everlight
git checkout mgn-pos-restore
cd 01_BUSINESSES/Everlight_Ventures/01_OnyxPOS/operations_MGN_v8
```

(If git asks about SSH keys, use the deploy key already set up, or clone the HTTPS URL
and sign in once.)

**Step 2 -- start it.**

```
./START_POS.sh start
```

That one command builds its own private Python environment, installs everything it
needs, and starts the server. First run takes a minute. After that it is instant.

**Step 3 -- open it.**

Open a browser on the same machine and go to:

```
http://localhost:5000
```

Log in as the owner: **Employee 1001, PIN 8008**. Change that PIN under Admin once you
are in (Admin -> reset PIN).

That is the whole install. `./START_POS.sh status` shows if it is running,
`./START_POS.sh logs` shows what it is doing, `./START_POS.sh restart` restarts it,
`./START_POS.sh stop` stops it.

---

## 3. Let the staff phones connect (shop WiFi)

By default the POS only answers on the machine it runs on -- that is the safe default.
To let phones on the shop WiFi reach it, start it like this instead:

```
HOST=0.0.0.0 ./START_POS.sh restart
```

Then find the machine's address on the WiFi:

- Mac/Linux: `hostname -I` (use the first number, e.g. `192.168.1.50`)
- Windows: `ipconfig` and read the "IPv4 Address"

On any staff phone (connected to the SAME shop WiFi) open the browser to:

```
http://192.168.1.50:5000      <- use YOUR machine's number
```

Bookmark it / add to home screen so it opens like an app.

**Security rule (important):** only do `HOST=0.0.0.0` on the private shop WiFi. Never
on public/guest WiFi. The POS should be reachable by staff phones and nothing else. If
the shop router has a "guest network", keep the POS off it.

---

## 4. Optional settings (.env) -- the app runs fine without any of these

Create a file named `.env` in this same folder to switch on the extras. Each line is
optional; leave one out and that feature just stays quiet. Secrets go here and ONLY
here -- never in the code, never in a spreadsheet, never in GitHub.

```
# --- Email receipts + end-of-day reports (uses a Gmail App Password, not your login) ---
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=mountaingardens@gmail.com
SMTP_PASS=your-16-char-app-password
SMTP_FROM=Mountain Gardens <mountaingardens@gmail.com>

# End-of-day close-out gets emailed to these (owner + mom). Comma-separated.
MGN_EOD_EMAIL=owner@example.com, mom@example.com

# --- Sales tax (set to YOUR county rate; food/veg plants are auto-exempt) ---
MGN_TAX_RATE=0.0825

# --- Login security (one random secret per machine; keeps logins from being forged) ---
# Leave blank and the app makes its own and saves it. Only set this if you want to
# share one value across machines on purpose.
# SECRET_KEY=

# --- Backups (a full copy is already saved at every till close; these are extras) ---
MGN_BACKUP_PASSPHRASE=pick-a-long-passphrase   # turns on AES-256 encryption
MGN_BACKUP_OFFSITE=/media/usb/mgn_backups       # auto-copy each backup to a USB/drive
```

After editing `.env`, run `./START_POS.sh restart` for it to take effect.

**Gmail App Password** (for receipts/EOD email): Google account -> Security -> 2-Step
Verification -> App passwords -> generate one for "Mail". Paste the 16 characters into
`SMTP_PASS`. This is NOT your normal Gmail password and can be revoked any time.

---

## 5. Daily operation

- **Open the till** in the morning, ring sales all day. Food/vegetable plants are not
  taxed; pots, soil, tools and ornamentals are -- the cart figures it out per line.
- **Customer + rewards:** at checkout you can attach a customer by email. They earn
  points (Bronze/Silver/Gold/Platinum multipliers) and can redeem points for a discount
  right at the register. Receipts email automatically if SMTP is set.
- **Close the till** at end of day. This writes the end-of-day report (and emails the 3
  copies if `MGN_EOD_EMAIL` is set) AND takes a full backup automatically.
- **Backups** also run on demand: Admin -> Backups -> "Back up now", and you can
  download any backup from there. Keep at least one copy off the machine (the USB
  `MGN_BACKUP_OFFSITE` does this for you).

Where the data lives: every CSV (sales, customers, inventory, payroll, schedule) is in
this folder's subfolders on the central machine. That is the single source of truth.

---

## 6. Keeping every machine identical (updates)

When new features ship, on each machine:

```
cd .../operations_MGN_v8
git pull
./START_POS.sh restart
```

Because all machines pull from the same GitHub branch, the Dell and the nursery PC
always have the exact same features. There is no "this one has X but that one doesn't".

---

## 7. If something looks wrong

- **Won't start:** `./START_POS.sh logs` shows the error. Most first-run issues are
  "Python not found" -- install Python 3 and re-run.
- **Phone can't reach it:** confirm you started with `HOST=0.0.0.0`, both devices are on
  the same shop WiFi, and you used the machine's real IP (not `localhost`) on the phone.
- **Forgot the owner PIN:** another admin can reset it under Admin. If no admin is
  available, the owner account is Employee 1001 -- a reset path is in the code owner's
  runbook.
- **Worried about data:** you are covered. A full backup is taken at every till close
  and any time you click "Back up now". Restore is just unzipping the latest
  `mgn_backup_*.tar.gz` back into this folder.

---

## What is NOT in software yet (needs you, not more code)

These are the only things between "tested" and "live at the counter". None are code
gaps -- they are inputs only you can provide:

1. **Real product catalog.** The current item list is mostly placeholder plant names.
   Import your real inventory (Admin -> Integrations -> import CSV) so tax auto-exempt
   and botanical names attach to actual products.
2. **Email credentials.** Receipts and the end-of-day email stay silent until you put a
   Gmail App Password in `.env` (Section 4).
3. **Mom's email address.** Add it to `MGN_EOD_EMAIL` so she gets the close-out copy.
4. **Card payments.** The register records Cash / Card / JIM today. A one-tap embedded
   card reader needs a Stripe (or Adyen) account and a certified reader -- that is a
   business sign-up, then a small code wire-up. Say the word when you have the account.
5. **Install at the shop.** Run Section 2 on the nursery PC, then Section 3 on the shop
   WiFi, then ring one test sale and one test till-close to confirm before go-live.
