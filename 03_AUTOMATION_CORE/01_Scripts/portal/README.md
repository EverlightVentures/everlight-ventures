# Everlight Organizational Portal

One lightweight local web server at `127.0.0.1:8800`.
Private by default (loopback bind -- network-binding doctrine).

## Addressing convention

```
http://127.0.0.1:8800/                          -- master index
http://127.0.0.1:8800/<NN>/                     -- category index
http://127.0.0.1:8800/<NN>/<subcategory>/       -- subcategory listing
http://127.0.0.1:8800/<NN>/<subcategory>/<file> -- serve file
```

`NN` is a two-digit zero-padded category number (01 to 100).

**Examples:**
- `http://127.0.0.1:8800/01/dashboards/SEND_APPROVAL_DASHBOARD.html`
- `http://127.0.0.1:8800/03/daily/performance_metrics.json`
- `http://127.0.0.1:8800/09/roster/` -- list roster files

## How to run

```bash
cd 03_AUTOMATION_CORE/01_Scripts/portal/
python3 portal_server.py
```

Or use the run script (foreground if interactive, background otherwise):

```bash
./run_portal.sh          # default port 8800
./run_portal.sh 8801     # custom port
PORTAL_PORT=8801 ./run_portal.sh
```

## Dependencies

- Python 3 (stdlib only for the server itself)
- PyYAML (`pip3 install pyyaml`) -- required to parse registry.yaml

## How to add a category

1. Open `registry.yaml`.
2. Add a new entry under `categories:` with a unique `number` (NN, two-digit).
3. Add subcategory slugs to `subcategories:`.
4. (Optional) Add `source_files:` entries to wire files from outside portal_root.
5. (Optional) Add `external_links:` for live apps on other ports.
6. Create the directory: `portal_root/<NN>/<subcat>/`
7. Restart the server.

## sdcard symlink note

Android sdcard (FAT32/exFAT) does NOT support POSIX symlinks.
Instead of copying files (which go stale), this server uses `source_files` in
registry.yaml. Files are streamed from their original paths at request time.
No copy, no stale data, no symlink required.

To add a file from anywhere on the filesystem:
```yaml
source_files:
  dashboards:
    - filename: MyReport.html
      source_path: /mnt/sdcard/AA_MY_DRIVE/_logs/inbound/MyReport.html
```

To serve files that are local to the portal tree, just drop them in
`portal_root/<NN>/<subcat>/` and they appear automatically.

## Running tests

```bash
cd 03_AUTOMATION_CORE/01_Scripts/portal/
python3 test_portal.py
```

## File map

```
portal/
  registry.yaml       -- source of truth for categories + source_files + external_links
  portal_server.py    -- HTTP server (stdlib + PyYAML)
  run_portal.sh       -- run script (foreground or background)
  test_portal.py      -- unit tests
  README.md           -- this file
  portal_root/        -- served static tree
    01/dashboards/    -- Wholesale: SEND_APPROVAL + pipeline sim (served from source_files)
    01/simulations/
    01/leads/
    02/dashboards/
    02/reports/
    03/daily/
    03/funnel/
    04/queue/
    04/published/
    05/rag/
    05/memory/
    06/status/
    06/logs/
    07/dashboards/
    07/queues/
    08/psa/
    08/signed/
    09/roster/
    09/sessions/
    10/dashboards/
```
