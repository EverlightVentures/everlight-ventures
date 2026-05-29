#!/usr/bin/env python3
"""
Portal unit tests -- stdlib only, no external deps.
Tests:
  1. registry.yaml parses and has expected categories
  2. render_master_index() produces valid HTML without error
  3. /01/dashboards/ resolves to a known source file (SEND_APPROVAL_DASHBOARD.html)
  4. Unknown /99/bogus/fake.html -> source_index miss (404 path)
  5. render_subcat_index() for a known subcat renders without error
  6. 404 page renders without error
"""

import sys
import os
from pathlib import Path

# Make sure we can import portal_server from the same directory
PORTAL_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(PORTAL_DIR))

import portal_server as ps
from portal_server import (
    load_registry,
    build_source_index,
    render_master_index,
    render_category_index,
    render_subcat_index,
    PortalHandler,
    PORTAL_ROOT,
)

PASS = "[PASS]"
FAIL = "[FAIL]"
failures = []

def check(name, condition, detail=""):
    if condition:
        print(f"  {PASS} {name}")
    else:
        print(f"  {FAIL} {name}{' -- ' + detail if detail else ''}")
        failures.append(name)


def test_registry_parses():
    print("\nTest 1: registry.yaml parses")
    cats = load_registry()
    check("categories is a list", isinstance(cats, list))
    check("at least 10 categories", len(cats) >= 10)
    numbers = [str(c.get("number", "")).zfill(2) for c in cats]
    check("category 01 present", "01" in numbers)
    check("category 02 present", "02" in numbers)
    check("category 05 present", "05" in numbers)
    # Each category has name + subcategories
    for cat in cats[:5]:
        nn = str(cat.get("number", "")).zfill(2)
        check(f"cat {nn} has name", bool(cat.get("name")))
        check(f"cat {nn} has subcategories", isinstance(cat.get("subcategories"), list))
    return cats


def test_source_index(cats):
    print("\nTest 2: source_index built correctly")
    idx = build_source_index(cats)
    check("source_index is a dict", isinstance(idx, dict))
    # SEND_APPROVAL_DASHBOARD.html should be in 01/dashboards
    key = ("01", "dashboards", "SEND_APPROVAL_DASHBOARD.html")
    check("SEND_APPROVAL_DASHBOARD in source_index", key in idx, f"keys: {list(idx.keys())[:5]}")
    key2 = ("01", "dashboards", "pipeline_simulation_dashboard.html")
    check("pipeline_simulation_dashboard in source_index", key2 in idx)
    # Source path should be a real path string
    if key in idx:
        check("source path is non-empty string", bool(idx[key]))
    return idx


def test_render_master_index(cats):
    print("\nTest 3: render_master_index() renders without error")
    html = render_master_index(cats)
    check("html is a string", isinstance(html, str))
    check("html has DOCTYPE", "<!DOCTYPE html>" in html)
    check("html has EVERLIGHT VENTURES", "EVERLIGHT VENTURES" in html)
    check("html has category 01", ">01<" in html or "01" in html)
    check("html has Wholesale", "Wholesale" in html)
    check("html has Trading", "Trading" in html)
    check("html not empty (>1000 chars)", len(html) > 1000)
    return html


def test_render_category_index(cats):
    print("\nTest 4: render_category_index() for cat 01")
    cat01 = next((c for c in cats if str(c.get("number", "")).zfill(2) == "01"), None)
    check("cat 01 found", cat01 is not None)
    if cat01:
        html = render_category_index(cat01)
        check("category html is string", isinstance(html, str))
        check("category html has subcategories", "dashboards" in html)
        check("category html has Wholesale", "Wholesale" in html)


def test_render_subcat_index(cats, idx):
    print("\nTest 5: render_subcat_index() for 01/dashboards")
    cat01 = next((c for c in cats if str(c.get("number", "")).zfill(2) == "01"), None)
    check("cat 01 found for subcat test", cat01 is not None)
    if cat01:
        html = render_subcat_index(cat01, "dashboards", PORTAL_ROOT, idx)
        check("subcat html is string", isinstance(html, str))
        check("subcat html has SEND_APPROVAL", "SEND_APPROVAL_DASHBOARD.html" in html)
        check("subcat html has breadcrumb", "breadcrumb" in html)


def test_source_path_resolves(idx):
    print("\nTest 6: known /01/dashboards/SEND_APPROVAL_DASHBOARD.html source resolves")
    key = ("01", "dashboards", "SEND_APPROVAL_DASHBOARD.html")
    if key in idx:
        sp = Path(idx[key])
        check("source file exists on disk", sp.is_file(), str(sp))
    else:
        check("key in source_index (SKIP file-exists check)", False, "key missing")

    key2 = ("01", "dashboards", "pipeline_simulation_dashboard.html")
    if key2 in idx:
        sp2 = Path(idx[key2])
        check("pipeline_sim source file exists", sp2.is_file(), str(sp2))


def test_unknown_path_misses_index(idx):
    print("\nTest 7: unknown /99/bogus/fake.html not in source_index (-> 404 path)")
    key = ("99", "bogus", "fake.html")
    check("99/bogus/fake.html NOT in source_index", key not in idx)


def test_404_render(cats):
    print("\nTest 8: 404 page renders without error")
    from portal_server import _html_shell
    html = _html_shell(
        "404 Not Found",
        '<nav class="breadcrumb"><a href="/">Portal</a> / 404</nav>',
        '<p class="section-title">404 -- Not Found</p><p>Test 404</p>',
    )
    check("404 html is string", isinstance(html, str))
    check("404 html has 404 text", "404" in html)


def test_http_server(cats, idx):
    """Spin up a live HTTPServer on an ephemeral port, send real requests, verify responses."""
    print("\nTest 9: live HTTP server (ephemeral port)")
    import http.server
    import threading
    import urllib.request
    import urllib.error

    PortalHandler.categories = cats
    PortalHandler.source_index = idx

    server = http.server.HTTPServer(("127.0.0.1", 0), PortalHandler)
    port = server.server_address[1]

    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    try:
        # GET /
        r = urllib.request.urlopen(f"http://127.0.0.1:{port}/")
        b = r.read().decode()
        check("GET / -> 200", r.status == 200)
        check("GET / has EVERLIGHT VENTURES", "EVERLIGHT VENTURES" in b)
        check("GET / has Wholesale", "Wholesale" in b)

        # GET /01/
        r2 = urllib.request.urlopen(f"http://127.0.0.1:{port}/01/")
        b2 = r2.read().decode()
        check("GET /01/ -> 200", r2.status == 200)
        check("GET /01/ has dashboards subcat", "dashboards" in b2)

        # GET /01/dashboards/ listing
        r3 = urllib.request.urlopen(f"http://127.0.0.1:{port}/01/dashboards/")
        b3 = r3.read().decode()
        check("GET /01/dashboards/ -> 200", r3.status == 200)
        check("GET /01/dashboards/ lists SEND_APPROVAL_DASHBOARD.html", "SEND_APPROVAL_DASHBOARD.html" in b3)

        # GET /01/dashboards/SEND_APPROVAL_DASHBOARD.html from source_files
        r4 = urllib.request.urlopen(
            f"http://127.0.0.1:{port}/01/dashboards/SEND_APPROVAL_DASHBOARD.html"
        )
        fdata = r4.read()
        check("GET /01/dashboards/SEND_APPROVAL_DASHBOARD.html -> 200", r4.status == 200)
        check("SEND_APPROVAL_DASHBOARD.html has content (>100 bytes)", len(fdata) > 100)
        print(f"    file size: {len(fdata):,} bytes")

        # GET /99/bogus/fake.html -> 404
        code404 = 0
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/99/bogus/fake.html")
        except urllib.error.HTTPError as e:
            code404 = e.code
        check("GET /99/bogus/fake.html -> 404", code404 == 404)

    finally:
        server.server_close()

    print(f"    (ephemeral test port was :{port})")


def main():
    print("=" * 55)
    print("  Everlight Portal -- Test Suite")
    print("=" * 55)

    cats = test_registry_parses()
    idx = test_source_index(cats)
    test_render_master_index(cats)
    test_render_category_index(cats)
    test_render_subcat_index(cats, idx)
    test_source_path_resolves(idx)
    test_unknown_path_misses_index(idx)
    test_404_render(cats)
    test_http_server(cats, idx)

    print("\n" + "=" * 55)
    if failures:
        print(f"  RESULT: {len(failures)} FAILED -- {failures}")
        sys.exit(1)
    else:
        print(f"  RESULT: ALL TESTS PASSED")
    print("=" * 55)


if __name__ == "__main__":
    main()
