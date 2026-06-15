import os
import pathlib
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]

@pytest.fixture
def fixture_path():
    return ROOT / "tests" / "fixtures" / "sample_registry.yaml"

@pytest.fixture(autouse=True)
def _chdir(monkeypatch):
    # tests reference fixture-relative paths from the package root
    monkeypatch.chdir(ROOT)
