import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from polymarket_agent.execution.wallet import PolygonWallet


def _stub_web3(monkeypatch):
    """Patch Web3 so constructor succeeds without real RPC."""
    fake_w3 = MagicMock()
    fake_w3.is_connected.return_value = True
    fake_w3.eth.chain_id = 137
    fake_w3.eth.contract.return_value = MagicMock()
    monkeypatch.setattr("polymarket_agent.execution.wallet.Web3", MagicMock(return_value=fake_w3))


def test_missing_key_file_fails_loud(tmp_path: Path):
    bad_path = tmp_path / "nope.key"
    with pytest.raises(RuntimeError) as e:
        PolygonWallet(private_key_path=bad_path)
    assert "key file missing" in str(e.value).lower()


def test_loads_address_from_valid_key(tmp_path: Path, monkeypatch):
    _stub_web3(monkeypatch)
    key_path = tmp_path / "test.key"
    key_path.write_text(
        "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    )
    os.chmod(key_path, 0o600)
    w = PolygonWallet(private_key_path=key_path)
    assert w.address.lower() == "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266"


def test_sign_typed_data_returns_hex_prefixed_signature(tmp_path, monkeypatch):
    _stub_web3(monkeypatch)
    key_path = tmp_path / "test.key"
    key_path.write_text(
        "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    )
    os.chmod(key_path, 0o600)
    w = PolygonWallet(private_key_path=key_path)
    typed = {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "chainId", "type": "uint256"},
            ],
            "Mail": [{"name": "contents", "type": "string"}],
        },
        "primaryType": "Mail",
        "domain": {"name": "Test", "chainId": 137},
        "message": {"contents": "hello"},
    }
    sig = w.sign_clob_order(typed)
    assert sig.startswith("0x")
    assert len(sig) == 132  # 0x + 130 hex = 65 bytes signature


def test_sign_clob_order_rejects_missing_keys(tmp_path, monkeypatch):
    _stub_web3(monkeypatch)
    key_path = tmp_path / "test.key"
    key_path.write_text(
        "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    )
    os.chmod(key_path, 0o600)
    w = PolygonWallet(private_key_path=key_path)
    with pytest.raises(RuntimeError) as e:
        w.sign_clob_order({"types": {}, "primaryType": "Mail"})  # missing domain + message
    assert "missing keys" in str(e.value).lower()


def test_sign_clob_order_rejects_wrong_chain_id(tmp_path, monkeypatch):
    _stub_web3(monkeypatch)
    key_path = tmp_path / "test.key"
    key_path.write_text(
        "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    )
    os.chmod(key_path, 0o600)
    w = PolygonWallet(private_key_path=key_path)
    typed = {
        "types": {"EIP712Domain": [{"name": "chainId", "type": "uint256"}], "M": []},
        "primaryType": "M",
        "domain": {"chainId": 1},
        "message": {},
    }
    with pytest.raises(RuntimeError) as e:
        w.sign_clob_order(typed)
    assert "chainid" in str(e.value).lower()


def test_invalid_key_text_raises_runtime(tmp_path):
    key_path = tmp_path / "test.key"
    key_path.write_text("not a key")
    os.chmod(key_path, 0o600)
    with pytest.raises(RuntimeError) as e:
        PolygonWallet(private_key_path=key_path)
    assert "64-hex" in str(e.value) or "private key" in str(e.value).lower()


def test_bad_perms_raises_runtime(tmp_path):
    key_path = tmp_path / "test.key"
    key_path.write_text(
        "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    )
    os.chmod(key_path, 0o644)
    with pytest.raises(RuntimeError) as e:
        PolygonWallet(private_key_path=key_path)
    assert "perms" in str(e.value).lower()


def test_key_not_reachable_on_instance(tmp_path, monkeypatch):
    """Regression guard: the raw private key must not be reachable via any
    public or single-attribute-hop path from a PolygonWallet instance.
    Original C2 finding plus residual __signer.__self__.key leak."""
    _stub_web3(monkeypatch)
    key_path = tmp_path / "test.key"
    key_path.write_text(
        "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    )
    import os; os.chmod(key_path, 0o600)
    w = PolygonWallet(private_key_path=key_path)

    # No public _account attribute
    assert not hasattr(w, "_account"), "instance must not retain LocalAccount"

    # The mangled __signer must not be a bound method on a LocalAccount
    signer = w._PolygonWallet__signer
    if hasattr(signer, "__self__"):
        # If anyone re-introduces a bound method, fail loud
        target = signer.__self__
        assert not hasattr(target, "key"), \
            f"bound method __self__ has .key attribute -- leak via {type(target).__name__}.key"
