import pytest
from pathlib import Path
from polymarket_agent.execution.wallet import PolygonWallet


def test_missing_key_file_fails_loud(tmp_path: Path):
    bad_path = tmp_path / "nope.key"
    with pytest.raises(RuntimeError) as e:
        PolygonWallet(private_key_path=bad_path)
    assert "key file missing" in str(e.value).lower()


def test_loads_address_from_valid_key(tmp_path: Path):
    # Test vector: well-known anvil/hardhat default key 0
    key_path = tmp_path / "test.key"
    key_path.write_text(
        "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    )
    w = PolygonWallet(private_key_path=key_path)
    assert w.address.lower() == "0xf39fd6e51aad88f6f4ce6ab8827279cfffb92266"
