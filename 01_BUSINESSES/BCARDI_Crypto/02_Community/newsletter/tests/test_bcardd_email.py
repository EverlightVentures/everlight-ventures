import sys, pathlib, pytest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from bcardd_email import build_intro_html, FUN_ONLY_DISCLAIMER, BANNED_FOUNDER_PHRASES

KW = dict(
    gift_url="https://alleykingz.online/bcardd/gift?code=PACK",
    unsub_url="https://example.com/u/abc",
    postal_address="Everlight Ventures LLC, 123 Registered Agent St, City, ST 00000",
)


def test_includes_fun_only_disclaimer():
    assert FUN_ONLY_DISCLAIMER in build_intro_html(**KW)


def test_includes_unsubscribe_link():
    html = build_intro_html(**KW)
    assert KW["unsub_url"] in html and "unsub" in html.lower()


def test_includes_postal_address():
    assert KW["postal_address"] in build_intro_html(**KW)


def test_includes_gift_link():
    assert KW["gift_url"] in build_intro_html(**KW)


def test_dog_voice_present():
    html = build_intro_html(**KW).lower()
    assert "$bcardd" in html and "dealer" in html


def test_no_founder_claims():
    html = build_intro_html(**KW).lower()
    for phrase in BANNED_FOUNDER_PHRASES:
        assert phrase not in html, f"founder-claim leaked: {phrase!r}"


def test_no_investment_language():
    html = build_intro_html(**KW).lower()
    for bad in ("financial advice is", "guaranteed return", "roi", "to the moon $", "buy now to profit"):
        assert bad not in html


@pytest.mark.parametrize("missing", ["gift_url", "unsub_url", "postal_address"])
def test_required_fields_raise(missing):
    kw = dict(KW)
    kw[missing] = ""
    with pytest.raises(ValueError):
        build_intro_html(**kw)


def test_send_intro_dry_run():
    from bcardd_email import send_intro
    out = send_intro(["someone@example.com"], gift_url="https://x/y",
                     unsub_url="https://x/u", postal_address="LLC, addr",
                     dry_run=True)
    assert out["dry_run"] is True and out["html_bytes"] > 200
