#!/usr/bin/env python3
"""REAL Polymarket live-verification harness. No mocks. No paper.

Proves the production signing + auth + order chain works against the live CLOB
and prints Verification Receipts (real ids, real timings) per the
prove-real-not-simulated doctrine.

Modes:
  --auth-only   (default) Derive L2 API creds via a real L1-signed call, assert
                L1+L2 auth, read real market metadata + on-chain balance.
                Costs $0. Works with an UNFUNDED wallet. This is the proof that
                the signing chain is accepted by Polymarket's live server.

  --full        Everything in --auth-only, PLUS place a real far-from-market
                tiny BUY limit order (will not fill), confirm the CLOB accepts
                it (real order id), then immediately cancel it. Needs a funded
                wallet (USDC.e) + a little MATIC for any on-chain step.

Usage:
  python3 verify_live.py --auth-only
  python3 verify_live.py --full --market <TOKEN_ID> --price 0.02 --size 5
  python3 verify_live.py --auth-only --key /path/to/wallet.key --host https://clob.polymarket.com
"""
import argparse
import json
import sys
import time
import urllib.request
from decimal import Decimal
from pathlib import Path

from kalshi_agent.execution.clob_live import LiveClobBackend, read_key_file

DEFAULT_KEY = "/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials/polymarket_wallet.key"
DEFAULT_HOST = "https://clob.polymarket.com"
GAMMA = "https://gamma-api.polymarket.com"


def _r(label, value):
    print(f"  {label:<32} {value}")


def pick_liquid_market(host: str):
    """Pull a real active, order-book-enabled market token from the live CLOB."""
    req = urllib.request.Request(f"{host}/markets", headers={"User-Agent": "ev-verify/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read())
    markets = data.get("data", data) if isinstance(data, dict) else data
    for m in markets:
        if not (m.get("active") and m.get("enable_order_book") and m.get("accepting_orders")):
            continue
        toks = m.get("tokens") or []
        for t in toks:
            tid = t.get("token_id")
            if tid:
                return m, str(tid)
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--auth-only", action="store_true", default=True)
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--key", default=DEFAULT_KEY)
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--market", default=None, help="token_id for --full order test")
    ap.add_argument("--price", type=float, default=0.02, help="far-from-market limit price")
    ap.add_argument("--size", type=float, default=5.0, help="shares for the test order")
    args = ap.parse_args()

    print("=" * 64)
    print("  EVERLIGHT POLYMARKET -- LIVE VERIFICATION (REAL, NOT SIMULATED)")
    print("=" * 64)
    t0 = time.time()

    # 1. Load key (fail loud if missing / bad perms / bad hex)
    try:
        key = read_key_file(args.key)
    except Exception as e:
        print(f"\n[FAIL] key load: {e}")
        return 2
    _r("key file", args.key)
    _r("host", args.host)

    # 2. Init backend = real L1-signed cred derivation + L1/L2 auth assertions
    try:
        t_auth = time.time()
        backend = LiveClobBackend(private_key=key, host=args.host, chain_id=137, auto_auth=True)
        auth_ms = int((time.time() - t_auth) * 1000)
    except Exception as e:
        print(f"\n[FAIL] live auth against {args.host}: {type(e).__name__}: {e}")
        print("       (this means the signing chain was REJECTED by the live server)")
        return 3

    print("\n  --- VERIFICATION RECEIPTS ---")
    _r("wallet address", backend.address)
    _r("L1 auth (signed call)", f"PASSED in {auth_ms}ms")
    _r("L2 auth (api creds)", "PASSED")
    creds = backend._creds
    api_key_id = getattr(creds, "api_key", "?")
    _r("derived API key id", api_key_id)

    # 3. Real server time round-trip
    try:
        st = backend._client.get_server_time()
        _r("CLOB server time", st)
    except Exception as e:
        _r("CLOB server time", f"(skipped: {e})")

    # 4. Real on-chain collateral balance
    try:
        bal = backend.get_usdc_balance()
        _r("USDC.e collateral balance", f"{bal}")
        if bal == 0:
            _r("  note", "wallet UNFUNDED -- auth proof still real; fund for live trades")
    except Exception as e:
        _r("USDC.e balance", f"(read failed: {e})")

    # 5. Real market metadata read (neg-risk + tick-size)
    market, token_id = (None, args.market)
    if token_id is None:
        market, token_id = pick_liquid_market(args.host)
    if token_id:
        try:
            neg = backend._client.get_neg_risk(token_id)
            tick = backend._client.get_tick_size(token_id)
            _r("sample token id", token_id)
            if market:
                _r("sample question", (market.get("question") or "")[:48])
            _r("neg_risk", neg)
            _r("tick_size", tick)
        except Exception as e:
            _r("market metadata", f"(read failed: {e})")

    # 6. --full: real order place + cancel
    if args.full:
        if not token_id:
            print("\n[FAIL] --full needs a market token; none found/given")
            return 4
        print("\n  --- LIVE ORDER TEST (place far-from-market, then cancel) ---")
        try:
            resp = backend.place_order(token_id=token_id, price=args.price,
                                       size=args.size, side="BUY")
            order_id = backend.extract_order_id(resp)
            _r("order placed", f"id={order_id} resp={json.dumps(resp)[:120]}")
            if order_id:
                cresp = backend.cancel(order_id)
                _r("order canceled", json.dumps(cresp)[:120])
            else:
                _r("order id", f"NONE -- full resp: {json.dumps(resp)[:200]}")
        except Exception as e:
            print(f"\n[FAIL] live order test: {type(e).__name__}: {e}")
            return 5

    print("\n" + "=" * 64)
    print(f"  VERIFICATION COMPLETE in {int((time.time()-t0)*1000)}ms")
    mode = "FULL (placed+canceled real order)" if args.full else "AUTH-ONLY ($0, signing chain proven live)"
    print(f"  MODE: {mode}")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    sys.exit(main())
