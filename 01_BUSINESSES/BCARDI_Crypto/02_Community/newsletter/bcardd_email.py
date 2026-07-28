"""$BCARDD "Day One" intro email: dog-voiced, fun-only, faceless.

Produces the INNER body HTML only. The outer luxury wrapper + Resend send +
all guards (resend_guard, resend_budget, phrase-scrub, send-authority) come
from content_tools.branded_mailer.send_branded_email().

CLI:
    python3 bcardd_email.py --preview          # write preview.html
    python3 bcardd_email.py --test you@x.com   # send one live test
"""
from __future__ import annotations

import os
import sys
import pathlib

# Jupiter "verified" heart-ask link, reused from _state/bcardd_ops/share.html
HEART_URL = "https://verified.jup.ag/dashboard/6mjokwXx7NNzo5ocvLDFGmbsGAs7rYHZdVJhKYkapump"

FUN_ONLY_DISCLAIMER = (
    "$BCARDD is a meme coin and a game, for fun and community, not an "
    "investment. DYOR. Never bet the rent."
)

# Faceless guard: the dog speaks, Rich never claims authorship.
BANNED_FOUNDER_PHRASES = (
    "i made", "i created", "i built this coin", "my coin",
    "i'm the founder", "i am the founder", "i launched",
)

BCARDD_FROM_EMAIL = os.environ.get("BCARDD_FROM_EMAIL", "dealer@everlightventures.io")
BCARDD_REPLY_TO = os.environ.get("BCARDD_REPLY_TO", BCARDD_FROM_EMAIL)
_SUBJECT = "You found me \U0001F0CF"  # "You found me 🃏"


def build_intro_html(*, gift_url: str, unsub_url: str, postal_address: str,
                     heart_url: str = HEART_URL) -> str:
    """Return the inner body HTML for the $BCARDD intro email.

    Raises ValueError if any legally/brand-required field is empty.
    """
    for name, val in (("gift_url", gift_url), ("unsub_url", unsub_url),
                      ("postal_address", postal_address)):
        if not val or not val.strip():
            raise ValueError(f"{name} is required")

    return f"""
<p style="font-size:18px;">You found me. \U0001F415\U0001F0CF</p>

<p>Name's <strong>$BCARDD</strong>, the B-Card Dog. The dealer. If this hit your
inbox, it's 'cause you grabbed the share kit, played a hand, or somebody in the
pack put you on.</p>

<p><em>Recognize the crew? &#8595;</em></p>
<p style="text-align:center;">
  <img src="https://alleykingz.online/bcardd/assets/montage.gif"
       alt="$BCARDD card drops + game clips" style="max-width:100%;border-radius:12px;">
</p>

<p>Here's the deal: I'm dealing you into the pack. Not a pitch, not financial
advice, just the most fun corner of the internet with a dog, a deck, and people
who actually show up.</p>

<p><strong>First one's on the house \U0001F381</strong> a little something on me:
<a href="{gift_url}">claim it here</a>.</p>

<p>Wanna help the pack grow? Tap a ❤️ on the page (counts real humans,
blocks bots): <a href="{heart_url}">right here</a>.</p>

<h3>What you get</h3>
<p>Card drops, game updates, memes that actually hit, and first dibs when
something new lands.</p>

<p>I only deal to people who wanna play. Not your vibe? No hard feelings,
<a href="{unsub_url}">fold here (unsubscribe)</a>.</p>

<h3>One thing before you go</h3>
<p>Hit reply and tell me your favorite hand, or the meme that put you on. I read
every one, and it tells me what to drop next.</p>

<p>Stay sharp,<br><strong>- $BCARDD \U0001F0CF</strong></p>

<hr>
<p style="font-size:12px;color:#8a8578;">{FUN_ONLY_DISCLAIMER}<br>
Everlight Ventures &middot; {postal_address} &middot;
<a href="{unsub_url}">unsubscribe</a></p>
""".strip()


def _load_mailer():
    """Locate content_tools/branded_mailer wherever this runs (phone or Oracle)."""
    root = pathlib.Path(__file__).resolve()
    for p in root.parents:
        ct = p / "03_AUTOMATION_CORE" / "01_Scripts" / "content_tools"
        if ct.exists():
            sys.path.insert(0, str(ct.parent))
            sys.path.insert(0, str(ct))
            break
    from content_tools.branded_mailer import send_branded_email  # type: ignore
    return send_branded_email


def send_intro(recipients, *, gift_url, unsub_url, postal_address, dry_run=False):
    """Build + send the intro email through the branded (guarded) Resend path.

    dry_run=True builds the HTML but sends nothing (no network, no import of
    the mailer), returning {"dry_run": True, "html_bytes": int}.
    """
    html = build_intro_html(gift_url=gift_url, unsub_url=unsub_url,
                            postal_address=postal_address)
    if dry_run:
        return {"dry_run": True, "html_bytes": len(html)}
    send = _load_mailer()
    return send(
        to=recipients, subject=_SUBJECT, content_html=html,
        from_name="$BCARDD \U0001F0CF", from_email=BCARDD_FROM_EMAIL,
        reply_to=BCARDD_REPLY_TO, budget_category="nurture",
    )


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--preview", action="store_true",
                    help="write preview HTML to ./preview.html")
    ap.add_argument("--test", metavar="EMAIL",
                    help="send one live test to this address")
    a = ap.parse_args()
    demo = dict(
        gift_url="https://alleykingz.online/bcardd/gift?code=PACK",
        unsub_url="https://alleykingz.online/bcardd/u/PREVIEW",
        postal_address=os.environ.get(
            "BCARDD_POSTAL_ADDRESS",
            "Everlight Ventures LLC, [registered-agent addr]"),
    )
    if a.preview:
        pathlib.Path("preview.html").write_text(build_intro_html(**demo))
        print("wrote preview.html")
    elif a.test:
        print(send_intro([a.test], **demo))
    else:
        ap.print_help()
