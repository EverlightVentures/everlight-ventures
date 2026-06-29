"""Kalshi signed execution layer (RSA-PSS auth) -- replaces execution/clob_live.py.

Proven live 2026-06-02: an authenticated /portfolio/balance call from a US IP
succeeds with no geoblock and no proxy (the whole reason we left Polymarket).
No web3, no wallet, no gas -- Kalshi is a clean USD balance behind an API key.

Auth (per Kalshi docs): for each request sign  timestamp_ms + METHOD + PATH  with
RSA-PSS (SHA-256, MGF1-SHA256, salt = digest length), base64 the signature, and
send headers KALSHI-ACCESS-KEY / -TIMESTAMP / -SIGNATURE. PATH includes the
/trade-api/v2 prefix and EXCLUDES the query string.
"""
import base64
import json
import time
import urllib.request
import urllib.error
import uuid
from pathlib import Path

BASE = "https://api.elections.kalshi.com"
PREFIX = "/trade-api/v2"


class KalshiAuthError(RuntimeError):
    pass


class KalshiClient:
    def __init__(self, key_id: str, private_key_path: str, base: str = BASE):
        from cryptography.hazmat.primitives import serialization
        self.key_id = key_id
        self.base = base
        raw = Path(private_key_path).read_bytes()
        try:
            self._key = serialization.load_pem_private_key(raw, password=None)
        except Exception as e:
            raise KalshiAuthError(f"bad Kalshi private key at {private_key_path}: {e}")

    # ---- auth ----
    def _headers(self, method: str, path: str) -> dict:
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding
        ts = str(int(time.time() * 1000))
        msg = (ts + method.upper() + path).encode()         # path EXCLUDES query string
        sig = self._key.sign(msg, padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                                              salt_length=hashes.SHA256().digest_size),
                             hashes.SHA256())
        return {"KALSHI-ACCESS-KEY": self.key_id, "KALSHI-ACCESS-TIMESTAMP": ts,
                "KALSHI-ACCESS-SIGNATURE": base64.b64encode(sig).decode(),
                "Content-Type": "application/json"}

    def _request(self, method: str, endpoint: str, body: dict = None):
        path = PREFIX + endpoint                            # signed path (no query)
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data,
                                     headers=self._headers(method, path), method=method)
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            detail = e.read().decode()[:300]
            raise KalshiAuthError(f"Kalshi {method} {endpoint} -> {e.code}: {detail}")

    # ---- reads ----
    def get_balance(self) -> float:
        """USD cash balance (dollars). The source of truth -- drift > $0.01 halts."""
        b = self._request("GET", "/portfolio/balance")
        return float(b.get("balance_dollars") or (b.get("balance", 0) / 100.0))

    def get_positions(self) -> list:
        return self._request("GET", "/portfolio/positions").get("market_positions", [])

    # ---- writes ----
    def place_order(self, ticker: str, side: str, action: str, count: int,
                    price_cents: int = None, post_only: bool = True,
                    tif: str = "good_till_canceled") -> dict:
        """Place an order via Kalshi's v2 single-book endpoint (/portfolio/events/orders).
        Kalshi deprecated the legacy /portfolio/orders (HTTP 410) -- migrated 2026-06-29.

        Back-compat signature (callers unchanged): side 'yes'/'no', action 'buy'/'sell',
        price_cents 1..99 (limit) or None (marketable). v2 quotes ONE yes book:
          bid = buy yes;  ask = sell yes ( == buy no at the inverted price ).
        So buy-no @ p maps to ask @ (100-p). Price is a fixed-point DOLLAR string, count a
        string. Maker-first by default (post_only -> ~75% cheaper fee, rests GTC); pass
        tif='immediate_or_cancel' to take. yes-side confirmed live (operator fill 2026-06-29);
        no-side is the documented bid/ask inversion."""
        buy = (action == "buy")
        if side == "yes":
            v2_side, yes_c = ("bid" if buy else "ask"), price_cents
        else:  # 'no': buy no == sell yes @ (100-p); sell no == buy yes @ (100-p)
            v2_side, yes_c = ("ask" if buy else "bid"), (None if price_cents is None else 100 - price_cents)
        body = {"ticker": ticker, "client_order_id": uuid.uuid4().hex, "side": v2_side,
                "count": "%d.00" % int(count),
                "time_in_force": "immediate_or_cancel" if yes_c is None else tif,
                "self_trade_prevention_type": "taker_at_cross"}
        if yes_c is not None:
            body["price"] = "%.4f" % (max(1, min(99, int(yes_c))) / 100.0)
            if post_only:
                body["post_only"] = True
        else:
            body["price"] = "0.9900" if v2_side == "bid" else "0.0100"  # marketable IOC
        resp = self._request("POST", "/portfolio/events/orders", body)
        return resp.get("order", resp) if isinstance(resp, dict) else resp

    def cancel_order(self, order_id: str) -> dict:
        return self._request("DELETE", f"/portfolio/orders/{order_id}")


def from_creds(creds_dir="/mnt/sdcard/AA_MY_DRIVE/03_AUTOMATION_CORE/03_Credentials"):
    """Build a client from the stored Key ID + private key (the proven setup)."""
    env = dict(l.split("=", 1) for l in Path(f"{creds_dir}/kalshi.env").read_text().splitlines() if "=" in l)
    return KalshiClient(env["KALSHI_KEY_ID"].strip(), f"{creds_dir}/kalshi_private_key.pem")
