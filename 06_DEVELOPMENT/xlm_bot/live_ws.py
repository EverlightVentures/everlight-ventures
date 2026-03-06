#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, separators=(",", ":"), default=str))
    tmp.replace(path)


@dataclass
class Tick:
    product_id: str
    price: float
    ts: str
    src: str = "coinbase_ws"


async def _run(product_id: str, out_path: Path, ws_url: str) -> None:
    import websockets  # type: ignore

    backoff = 1.0
    while True:
        try:
            async with websockets.connect(ws_url, ping_interval=20, ping_timeout=20) as ws:
                sub = {
                    "type": "subscribe",
                    "channels": [{"name": "ticker", "product_ids": [product_id]}],
                }
                await ws.send(json.dumps(sub))

                backoff = 1.0
                last_write = 0.0
                while True:
                    raw = await ws.recv()
                    now = time.time()
                    try:
                        msg = json.loads(raw)
                    except Exception:
                        continue

                    if msg.get("type") != "ticker":
                        continue
                    if msg.get("product_id") != product_id:
                        continue
                    p = msg.get("price")
                    try:
                        price = float(p)
                    except Exception:
                        continue

                    # Coinbase ticker messages carry an ISO timestamp under "time".
                    ts = msg.get("time") or _utc_now_iso()
                    tick = Tick(product_id=product_id, price=price, ts=str(ts))

                    # Throttle disk writes slightly to avoid hammering storage.
                    if now - last_write >= 0.25:
                        _atomic_write_json(
                            out_path,
                            {
                                "product_id": tick.product_id,
                                "price": tick.price,
                                "timestamp": tick.ts,
                                "src": tick.src,
                                "written_at": _utc_now_iso(),
                            },
                        )
                        last_write = now
        except Exception as e:
            _atomic_write_json(
                out_path,
                {
                    "product_id": product_id,
                    "price": None,
                    "timestamp": None,
                    "src": "coinbase_ws",
                    "error": str(e),
                    "written_at": _utc_now_iso(),
                },
            )
            # Exponential backoff with jitter.
            sleep_s = min(30.0, backoff) + random.random() * 0.5
            time.sleep(sleep_s)
            backoff = min(30.0, backoff * 1.7)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--product", default="XLM-USD")
    p.add_argument("--out", default=str(Path(__file__).parent / "logs" / "live_tick.json"))
    p.add_argument("--ws-url", default="wss://ws-feed.exchange.coinbase.com")
    args = p.parse_args()

    out_path = Path(args.out)

    # Write a startup marker so the dashboard can show "ws online" quickly.
    _atomic_write_json(
        out_path,
        {
            "product_id": args.product,
            "price": None,
            "timestamp": None,
            "src": "coinbase_ws",
            "status": "starting",
            "written_at": _utc_now_iso(),
        },
    )

    import asyncio

    asyncio.run(_run(product_id=args.product, out_path=out_path, ws_url=args.ws_url))


if __name__ == "__main__":
    main()

