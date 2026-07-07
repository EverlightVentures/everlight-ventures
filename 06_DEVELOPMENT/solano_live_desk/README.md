# Solano Live Desk (Phase 1)

Personal live map of Solano County CHP incidents. Free, public data only.

## Run
    pip install -r requirements.txt
    bash scripts/run.sh          # ingest loop + API on 127.0.0.1:2600
    # open http://127.0.0.1:2600

Env: `SLD_STORE` (day-DB dir, default ./store), `PORT` (default 2600),
`EV_BIND=0.0.0.0` to expose on tailnet for the phone.

## Test
    python3 -m pytest -q

## Sources
- CHP incidents: http://media.chp.ca.gov/sa_xml/sa.xml (public, no auth)

See docs/2026-07-07-solano-live-desk-design.md for the full design.
