# tests/test_sync.py
import pathlib
from registry import load_registry
import sync

MARK = ("# LX:START", "# LX:END")

def test_inject_block_is_idempotent(tmp_path):
    f = tmp_path / "x.sh"
    f.write_text("a\n# LX:START\nOLD\n# LX:END\nb\n")
    sync.inject_block(f, MARK, "NEW")
    sync.inject_block(f, MARK, "NEW")  # twice -> same result
    out = f.read_text()
    assert out.count("# LX:START") == 1
    assert "NEW" in out and "OLD" not in out
    assert out.startswith("a\n") and out.rstrip().endswith("b")

def test_run_sync_dry_run_writes_nothing(fixture_path, tmp_path, monkeypatch):
    reg = load_registry(fixture_path)
    target = tmp_path / "banner.sh"
    target.write_text("# LX:DASH:START\n# LX:DASH:END\n")
    monkeypatch.setattr(sync, "SHELL_BANNER", target)
    changed = sync.run_sync(reg, dry_run=True)
    assert "banner.sh" in "".join(changed)            # reports it WOULD change
    assert target.read_text() == "# LX:DASH:START\n# LX:DASH:END\n"  # unchanged

def test_inject_block_raises_on_orphaned_marker(tmp_path):
    f = tmp_path / "x.sh"
    f.write_text("a\n# LX:START\nOLD\nb\n")   # start present, end missing
    import pytest
    with pytest.raises(ValueError):
        sync.inject_block(f, MARK, "NEW")

def test_run_sync_fails_closed_on_invalid_registry(fixture_path, tmp_path, monkeypatch):
    reg = load_registry(fixture_path)
    reg.dashboards[0].access = "world"                # invalid
    target = tmp_path / "banner.sh"
    target.write_text("# LX:DASH:START\n# LX:DASH:END\n")
    css = tmp_path / "lucrex.css"
    css.write_text("/* LUCREX-OS:TOKENS:START */\n/* LUCREX-OS:TOKENS:END */\n")
    monkeypatch.setattr(sync, "SHELL_BANNER", target)
    monkeypatch.setattr(sync, "LUCREX_CSS", css)
    import pytest
    with pytest.raises(SystemExit):
        sync.run_sync(reg, dry_run=False)
    assert target.read_text() == "# LX:DASH:START\n# LX:DASH:END\n"
    assert css.read_text() == "/* LUCREX-OS:TOKENS:START */\n/* LUCREX-OS:TOKENS:END */\n"

def test_token_injection_writes_root_block(fixture_path, tmp_path, monkeypatch):
    reg = load_registry(fixture_path)
    css = tmp_path / "lucrex.css"
    css.write_text("/* LUCREX-OS:TOKENS:START */\n/* LUCREX-OS:TOKENS:END */\nbody{}\n")
    banner = tmp_path / "banner.sh"
    banner.write_text("# LX:DASH:START\n# LX:DASH:END\n")
    monkeypatch.setattr(sync, "LUCREX_CSS", css)
    monkeypatch.setattr(sync, "SHELL_BANNER", banner)
    sync.run_sync(reg, dry_run=False)
    assert "--gold: #D4AF37;" in css.read_text()       # tokens injected -> dashboard is styled

def test_inject_block_appends_when_no_markers(tmp_path):
    f = tmp_path / "x.sh"
    f.write_text("alpha\nbeta\n")
    sync.inject_block(f, MARK, "NEW")
    out = f.read_text()
    assert out.startswith("alpha\nbeta")
    assert "# LX:START\nNEW\n# LX:END" in out
    assert out.count("# LX:START") == 1

def test_main_skips_when_registry_absent(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sync, "OS_DIR", tmp_path)   # tmp_path has no registry.yaml
    rc = sync.main([])
    assert rc == 0
    assert "not found" in capsys.readouterr().out
