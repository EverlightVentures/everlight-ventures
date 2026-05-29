"""Tests for LiveClobBackend -- the real py-clob-client execution path.

ClobClient is mocked so these run offline. The live signing chain is proven
separately by verify_live.py against the real CLOB (real receipts, no mocks)."""
import json
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch
import os
import pytest

from polymarket_agent.execution.clob_live import (
    LiveClobBackend, read_key_file, KeyFileError,
)


# ---- key file loading (reuses wallet.py validation posture) ----

def test_read_key_file_missing_raises(tmp_path):
    with pytest.raises(KeyFileError) as e:
        read_key_file(tmp_path / "nope.key")
    assert "missing" in str(e.value).lower()


def test_read_key_file_world_readable_raises(tmp_path):
    p = tmp_path / "k.key"
    p.write_text("0x" + "a" * 64)
    os.chmod(p, 0o644)  # world-readable -> forbidden
    with pytest.raises(KeyFileError) as e:
        read_key_file(p)
    assert "world" in str(e.value).lower() or "perms" in str(e.value).lower()


def test_read_key_file_group_only_ok(tmp_path):
    """0o660 (no world bits) is tolerated -- sdcard/exFAT floor."""
    p = tmp_path / "k.key"
    p.write_text("0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80")
    os.chmod(p, 0o660)
    key = read_key_file(p)
    assert key.startswith("0x")


def test_read_key_file_bad_hex_raises(tmp_path):
    p = tmp_path / "k.key"
    p.write_text("not a hex key")
    os.chmod(p, 0o600)
    with pytest.raises(KeyFileError) as e:
        read_key_file(p)
    assert "hex" in str(e.value).lower() or "private key" in str(e.value).lower()


def test_read_key_file_valid(tmp_path):
    p = tmp_path / "k.key"
    p.write_text("0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80")
    os.chmod(p, 0o600)
    key = read_key_file(p)
    assert key.startswith("0x")
    assert len(key) == 66


# ---- LiveClobBackend (ClobClient mocked) ----

def _make_backend(monkeypatch, **client_overrides):
    fake_client = MagicMock()
    fake_client.get_address.return_value = "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266"
    fake_creds = MagicMock(api_key="ak", api_secret="as", api_passphrase="ap")
    fake_client.create_or_derive_api_creds.return_value = fake_creds
    # MagicMock blocks auto-attrs starting with "assert"; the real ClobClient
    # has these methods, so assign them explicitly.
    fake_client.assert_level_1_auth = MagicMock()
    fake_client.assert_level_2_auth = MagicMock()
    for k, v in client_overrides.items():
        setattr(fake_client, k, v)
    monkeypatch.setattr(
        "polymarket_agent.execution.clob_live.ClobClient",
        MagicMock(return_value=fake_client),
    )
    backend = LiveClobBackend(
        private_key="0x" + "a" * 64,
        host="https://clob.polymarket.com",
        chain_id=137,
        auto_auth=True,
    )
    return backend, fake_client


def test_init_derives_and_sets_creds_and_asserts_auth(monkeypatch):
    backend, fake = _make_backend(monkeypatch)
    assert fake.create_or_derive_api_creds.call_count == 1
    assert fake.set_api_creds.call_count == 1
    assert fake.assert_level_1_auth.call_count == 1
    assert fake.assert_level_2_auth.call_count == 1
    assert backend.authed is True
    assert backend.address == "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266"


def test_auto_auth_false_skips_auth(monkeypatch):
    fake_client = MagicMock()
    fake_client.get_address.return_value = "0xabc"
    monkeypatch.setattr(
        "polymarket_agent.execution.clob_live.ClobClient",
        MagicMock(return_value=fake_client),
    )
    backend = LiveClobBackend(private_key="0x" + "a" * 64,
                              host="h", chain_id=137, auto_auth=False)
    assert fake_client.create_or_derive_api_creds.call_count == 0
    assert backend.authed is False


def test_get_usdc_balance_converts_6_decimals(monkeypatch):
    backend, fake = _make_backend(monkeypatch)
    fake.get_balance_allowance.return_value = {"balance": "250000000"}  # 250 USDC.e raw
    bal = backend.get_usdc_balance()
    assert bal == Decimal("250")


def test_place_order_uses_neg_risk_and_tick_size(monkeypatch):
    backend, fake = _make_backend(monkeypatch)
    fake.get_neg_risk.return_value = True
    fake.get_tick_size.return_value = "0.01"
    fake.create_order.return_value = {"signed": "order"}
    fake.post_order.return_value = {"success": True, "orderID": "0xORDER123"}

    resp = backend.place_order(token_id="123", price=0.5, size=20.0, side="BUY")

    # neg-risk + tick-size were queried for this token
    fake.get_neg_risk.assert_called_once_with("123")
    fake.get_tick_size.assert_called_once_with("123")
    # create_order was called with options carrying the queried neg_risk + tick
    _, kwargs = fake.create_order.call_args
    opts = kwargs.get("options") or fake.create_order.call_args[0][1]
    assert opts.neg_risk is True
    assert opts.tick_size == "0.01"
    # post_order called with the signed order
    assert fake.post_order.call_count == 1
    assert resp["orderID"] == "0xORDER123"


def test_extract_order_id_handles_variants(monkeypatch):
    backend, _ = _make_backend(monkeypatch)
    assert backend.extract_order_id({"orderID": "a"}) == "a"
    assert backend.extract_order_id({"orderId": "b"}) == "b"
    assert backend.extract_order_id({"id": "c"}) == "c"
    assert backend.extract_order_id({}) is None
    assert backend.extract_order_id(None) is None


def test_place_order_rejects_nonpositive_inputs(monkeypatch):
    backend, _ = _make_backend(monkeypatch)
    with pytest.raises(ValueError):
        backend.place_order(token_id="123", price=0, size=10, side="BUY")
    with pytest.raises(ValueError):
        backend.place_order(token_id="123", price=0.5, size=0, side="BUY")


def test_cancel_delegates(monkeypatch):
    backend, fake = _make_backend(monkeypatch)
    fake.cancel.return_value = {"canceled": ["0xORDER123"]}
    out = backend.cancel("0xORDER123")
    fake.cancel.assert_called_once_with("0xORDER123")
    assert out["canceled"] == ["0xORDER123"]
