import os
from everlense import paths

def test_photo_root_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("EVERLENSE_PHOTO_ROOT", str(tmp_path))
    assert paths.photo_root() == tmp_path
    assert paths.state_dir() == tmp_path / ".everlense"
    assert paths.trash_dir() == tmp_path / "_Trash"

def test_dcim_sources_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("EVERLENSE_DCIM", str(tmp_path))
    srcs = paths.dcim_sources()
    assert tmp_path / "Camera" in srcs
    assert tmp_path / "Screenshots" in srcs
