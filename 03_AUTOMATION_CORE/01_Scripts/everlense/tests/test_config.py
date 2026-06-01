from everlense import config

def test_categories_seed_on_first_run(tmp_path, monkeypatch):
    monkeypatch.setenv("EVERLENSE_PHOTO_ROOT", str(tmp_path))
    cats = config.load_categories()
    assert "Linux" in cats and "AI" in cats
    assert any("sudo" in kw for kw in cats["Linux"]["keywords"])
    # second load reads the now-seeded file, not defaults
    assert (tmp_path / ".everlense" / "categories.yaml").exists()

def test_projects_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("EVERLENSE_PHOTO_ROOT", str(tmp_path))
    config.save_project({"slug": "2026-05_123-main", "address": "123 Main St", "watermark": True})
    projs = config.load_projects()
    assert projs["2026-05_123-main"]["address"] == "123 Main St"

def test_state_cursor(tmp_path, monkeypatch):
    monkeypatch.setenv("EVERLENSE_PHOTO_ROOT", str(tmp_path))
    st = config.load_state()
    assert st["known_hashes"] == []
    st["known_hashes"].append("abc")
    config.save_state(st)
    assert "abc" in config.load_state()["known_hashes"]
