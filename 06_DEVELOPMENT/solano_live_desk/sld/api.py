from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from . import store

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(title="Solano Live Desk")


def _store_dir() -> str:
    return os.environ.get("SLD_STORE", "store")


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/api/days")
def days():
    return {"days": store.list_days(_store_dir())}


@app.get("/api/events")
def events(date: str | None = None):
    base = _store_dir()
    day = date or store.today_pt()
    if not store.day_db_path(base, day).exists():
        return {"date": day, "events": []}
    conn = store.connect(base, day)
    try:
        return {"date": day, "events": store.get_events(conn)}
    finally:
        conn.close()


# Serve the static web page at "/" (index.html). Mounted last so /api and
# /healthz win. Guard so the app imports even before web/ exists.
if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
