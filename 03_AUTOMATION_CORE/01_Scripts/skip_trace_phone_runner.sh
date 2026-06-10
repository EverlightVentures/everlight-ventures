#!/usr/bin/env bash
# skip_trace_phone_runner.sh
# Runs on the PHONE (Termux). When Oracle's datacenter IP gets anti-bot-walled
# by people-search sites, Oracle drops a JSON in /home/opc/_skip_trace_pending/.
# This script:
#   1. SSH's into Oracle, lists pending requests
#   2. Downloads each request, runs the same scrapers from the phone's
#      residential IP (TruePeopleSearch, FastPeopleSearch, ZabaSearch, Whitepages)
#   3. SCPs the result JSON back to /home/opc/_skip_trace_results/{lead_id}.json
#   4. Removes the pending request from Oracle so we don't double-process
#
# Flags:
#   --dry    Print what would happen, don't upload anything
#   --max=N  Process at most N requests this run (default 10)
#
# Compiled by Rex Blackwell. Lucrex serves the King of Divine Light.

set -uo pipefail

ORACLE_HOST="opc@163.192.19.196"
SSH_KEY="/root/.ssh/oracle_key.pem"
SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=10 -i ${SSH_KEY}"
ORACLE_PENDING="/home/opc/_skip_trace_pending"
ORACLE_RESULTS="/home/opc/_skip_trace_results"
WORK_DIR="/data/data/com.termux/files/home/_skip_trace_workdir"
LOG_FILE="${WORK_DIR}/runner.log"
SCRAPER_PY="${WORK_DIR}/phone_scraper.py"

DRY=0
MAX_PROCESS=10
for a in "$@"; do
  case "$a" in
    --dry) DRY=1 ;;
    --max=*) MAX_PROCESS="${a#--max=}" ;;
  esac
done

mkdir -p "${WORK_DIR}"
log()  { echo "$(date -Iseconds) | $*" | tee -a "${LOG_FILE}"; }
ssh_o() { ssh ${SSH_OPTS} "${ORACLE_HOST}" "$@"; }
scp_to_oracle() { scp ${SSH_OPTS} "$1" "${ORACLE_HOST}:$2"; }

# Lazily drop the phone-side scraper Python next to this script.
# This is identical to Oracle's logic but standalone (no Django dependency).
cat > "${SCRAPER_PY}" <<'PYEOF'
#!/usr/bin/env python3
"""Phone-side standalone scraper. Reads request JSON on stdin, writes result JSON on stdout."""
import json, random, re, sys, time
import requests

USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
]
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"\(?(\d{3})\)?[\s.\-]?(\d{3})[\s.\-]?(\d{4})")

def get(url):
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        r = requests.get(url, headers=headers, timeout=15)
        return r.status_code, r.text
    except Exception as e:
        return 0, f"ERR:{e}"

def extract_emails(t):
    if not t: return []
    out, seen = [], set()
    for e in EMAIL_RE.findall(t):
        en = e.lower().strip(".,;:")
        if any(j in en for j in ["@example.","@yoursite","@sentry.io","@cloudflare",
                                  "@google-analytics","noreply@","no-reply@",
                                  "support@truepeople","support@fastpeople",
                                  ".png",".jpg",".gif",".svg"]):
            continue
        if en not in seen:
            seen.add(en); out.append(en)
    return out

def extract_phones(t):
    if not t: return []
    out, seen = [], set()
    for a, b, c in PHONE_RE.findall(t):
        if a in ("000","111","555") or len(set(a+b+c)) == 1: continue
        if a[0] in ("0","1"): continue
        full = f"{a}-{b}-{c}"
        if full not in seen:
            seen.add(full); out.append(full)
    return out

def truepeoplesearch(name, addr, city, state):
    if not (name and city and state): return ("no_data", [], [])
    url = f"https://www.truepeoplesearch.com/results?name={'+'.join(name.split())}&citystatezip={city.replace(' ','+')},{state}"
    code, html = get(url)
    if code in (403,429,503): return ("blocked", [], [])
    if code != 200: return ("error", [], [])
    if "captcha" in (html or "").lower(): return ("blocked", [], [])
    return ("found", extract_emails(html), extract_phones(html))

def fastpeoplesearch(name, addr, city, state):
    if not (name and city and state): return ("no_data", [], [])
    url = f"https://www.fastpeoplesearch.com/name/{name.lower().replace(' ','-')}_{city.lower().replace(' ','-').replace('.','')}-{state.lower()}"
    code, html = get(url)
    if code in (403,429,503): return ("blocked", [], [])
    if code != 200: return ("error", [], [])
    if "captcha" in (html or "").lower(): return ("blocked", [], [])
    return ("found", extract_emails(html), extract_phones(html))

def zabasearch(name, addr, city, state):
    if not (name and state): return ("no_data", [], [])
    parts = name.split()
    first = parts[0] if parts else ""
    last  = parts[-1] if len(parts) > 1 else ""
    url = f"https://www.zabasearch.com/people/{first}+{last}/{state}/"
    code, html = get(url)
    if code in (403,429,503): return ("blocked", [], [])
    if code != 200: return ("error", [], [])
    if "captcha" in (html or "").lower(): return ("blocked", [], [])
    return ("found", extract_emails(html), extract_phones(html))

def whitepages(name, addr, city, state):
    if not (name and city and state): return ("no_data", [], [])
    url = f"https://www.whitepages.com/name/{name.replace(' ','-')}/{city.replace(' ','-')}-{state}"
    code, html = get(url)
    if code in (403,429,503): return ("blocked", [], [])
    if code != 200: return ("error", [], [])
    if "captcha" in (html or "").lower(): return ("blocked", [], [])
    return ("found", extract_emails(html), extract_phones(html))

SOURCES = [("truepeoplesearch", truepeoplesearch),
           ("fastpeoplesearch", fastpeoplesearch),
           ("zabasearch",       zabasearch),
           ("whitepages",       whitepages)]

def main():
    req = json.load(sys.stdin)
    name  = req.get("owner_name","")
    addr  = req.get("address","")
    city  = req.get("city","")
    state = req.get("state","")
    found_emails, found_phones, src_used, per_source = [], [], None, []
    for sname, fn in SOURCES:
        try:
            status, emails, phones = fn(name, addr, city, state)
        except Exception as e:
            status, emails, phones = ("error", [], [])
        per_source.append({"source": sname, "status": status,
                           "emails": len(emails), "phones": len(phones)})
        if status == "found" and (emails or phones):
            if not found_emails: found_emails = emails
            if not found_phones: found_phones = phones
            if not src_used: src_used = sname
        time.sleep(3 + random.uniform(0, 1.5))
        if found_emails and found_phones:
            break
    out = {
        "lead_id": req.get("lead_id"),
        "emails": found_emails,
        "phones": found_phones,
        "source": src_used or "phone_relay_no_data",
        "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "per_source_summary": per_source,
    }
    json.dump(out, sys.stdout)
    sys.stdout.write("\n")

if __name__ == "__main__":
    main()
PYEOF
chmod +x "${SCRAPER_PY}"

log "RUN_START dry=${DRY} max=${MAX_PROCESS}"

# 1. List pending requests on Oracle
PENDING=$(ssh_o "ls -1 ${ORACLE_PENDING}/*.json 2>/dev/null | head -${MAX_PROCESS}")
if [ -z "${PENDING}" ]; then
  log "NO_PENDING"
  echo "No pending requests."
  exit 0
fi

count=0
processed=0
ingested=0
for remote_path in ${PENDING}; do
  count=$((count+1))
  fname=$(basename "${remote_path}")
  log "PROCESSING ${fname}"

  # 2. Download the request
  local_req="${WORK_DIR}/${fname}"
  if ! scp ${SSH_OPTS} "${ORACLE_HOST}:${remote_path}" "${local_req}" 2>>"${LOG_FILE}"; then
    log "DOWNLOAD_FAIL ${fname}"
    continue
  fi

  # 3. Run the scraper locally (residential IP)
  local_res="${WORK_DIR}/result_${fname}"
  if ! python3 "${SCRAPER_PY}" < "${local_req}" > "${local_res}" 2>>"${LOG_FILE}"; then
    log "SCRAPER_FAIL ${fname}"
    continue
  fi
  processed=$((processed+1))

  # 4. Show what we got (always)
  echo "--- ${fname} ---"
  cat "${local_res}"
  echo

  if [ "${DRY}" -eq 1 ]; then
    log "DRY_SKIP_UPLOAD ${fname}"
    continue
  fi

  # 5. Upload result + remove pending
  if scp_to_oracle "${local_res}" "${ORACLE_RESULTS}/${fname}" >>"${LOG_FILE}" 2>&1; then
    ssh_o "rm -f ${remote_path}"
    ingested=$((ingested+1))
    log "RELAY_DONE ${fname}"
  else
    log "UPLOAD_FAIL ${fname}"
  fi

  # Polite gap between leads
  sleep 2
done

log "RUN_DONE listed=${count} processed=${processed} uploaded=${ingested}"
echo "Listed=${count} Processed=${processed} Uploaded=${ingested}"
