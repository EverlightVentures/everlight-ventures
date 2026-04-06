#!/usr/bin/env python3
"""
Broker OS -- Contact Enrichment Module

Extracts REAL contact info (emails, profile URLs, websites) from public sources
instead of generating placeholder emails.

Sources (all free, no API keys needed):
  - GitHub API (unauthenticated, 60 req/hr): public email, blog, twitter
  - GitHub Events API: commit emails from public push events
  - HN Firebase API: user about field (often contains email/website)
  - DEV.to API: author profile (website, github, twitter)
  - Reddit: profile URL (no email available via API)
  - Page scraping: email patterns from personal websites

Returns a ContactInfo dict with:
  - email: real email if found, else ""
  - profile_url: best profile URL for manual follow-up
  - website: personal website if found
  - twitter: twitter/X handle if found
  - github: github profile URL if found
  - needs_enrichment: True if no real email found
  - contact_method: "email" | "profile" | "none"
"""
import json
import logging
import re
import time
import urllib.request
import urllib.error

log = logging.getLogger("broker.enrichment")

UA = "EverLight-BrokerOS/1.0"

# Rate limit tracking for GitHub (60 req/hr unauthenticated)
_gh_requests = []
GH_RATE_LIMIT = 55  # leave 5 buffer


def _fetch_json(url, timeout=10):
    """Fetch JSON from URL with User-Agent header."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 403:
            log.warning("Rate limited: %s", url[:80])
        else:
            log.debug("HTTP %d: %s", e.code, url[:80])
        return None
    except Exception as e:
        log.debug("Fetch failed %s: %s", url[:60], e)
        return None


def _fetch_text(url, timeout=10, max_bytes=15000):
    """Fetch raw text from URL."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read(max_bytes).decode("utf-8", errors="ignore")
    except Exception:
        return ""


def _gh_rate_ok():
    """Check if we can make another GitHub API request."""
    global _gh_requests
    now = time.time()
    _gh_requests = [t for t in _gh_requests if now - t < 3600]
    return len(_gh_requests) < GH_RATE_LIMIT


def _gh_track():
    """Track a GitHub API request."""
    _gh_requests.append(time.time())


def extract_email_from_text(text):
    """Extract a plausible personal email from text. Filters junk."""
    if not text:
        return ""
    # Strip HTML tags first
    clean = re.sub(r'<[^>]+>', ' ', text)

    # Find all email-like patterns
    candidates = re.findall(r'[\w.+-]+@[\w-]+\.[\w.-]+', clean)
    if not candidates:
        return ""

    # Filter bad ones
    bad_tlds = (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".css", ".js", ".html")
    skip_patterns = [
        "noreply", "no-reply", "github-noreply", "notifications@",
        "hn@ycombinator.com", "support@", "info@", "hello@",
        "contact@", "admin@", "help@", "team@", "sales@",
        "press@", "media@", "abuse@", "security@", "postmaster@",
        "webmaster@", "mailer-daemon@", "donotreply",
        "@placeholder.io", "@example.com", "@users.noreply",
    ]

    for email in candidates:
        email = email.lower().rstrip(".")
        if any(email.endswith(ext) for ext in bad_tlds):
            continue
        if any(s in email for s in skip_patterns):
            continue
        tld = email.rsplit(".", 1)[-1]
        if len(tld) < 2 or len(tld) > 6:
            continue
        if "//" in email or "http" in email:
            continue
        # Must have reasonable local part
        local = email.split("@")[0]
        if len(local) < 2:
            continue
        return email
    return ""


def extract_urls_from_text(text):
    """Extract URLs from text."""
    if not text:
        return []
    clean = re.sub(r'<[^>]+>', ' ', text)
    urls = re.findall(r'https?://[^\s<>"\')\]]+', clean)
    return [u.rstrip(".,;:") for u in urls]


# ---------------------------------------------------------------------------
# GitHub enrichment
# ---------------------------------------------------------------------------

def enrich_github_user(login):
    """
    Get real contact info from a GitHub user profile.
    Uses:
      1. /users/{login} -- public email, blog, twitter, name, company
      2. /users/{login}/events/public -- commit emails from push events
    """
    if not login or not _gh_rate_ok():
        return {}

    result = {}
    _gh_track()
    user = _fetch_json(f"https://api.github.com/users/{login}")
    if not user:
        return {}

    # Direct fields
    result["name"] = user.get("name") or login
    result["company"] = user.get("company") or ""
    result["profile_url"] = f"https://github.com/{login}"

    # Public email (many devs have this set)
    email = user.get("email") or ""
    if email and "@" in email:
        result["email"] = email

    # Blog/website
    blog = (user.get("blog") or "").strip()
    if blog:
        if not blog.startswith("http"):
            blog = f"https://{blog}"
        result["website"] = blog
        # Sometimes blog field IS an email
        if "@" in blog and "http" not in blog:
            result["email"] = blog.replace("https://", "").replace("http://", "")

    # Twitter
    twitter = user.get("twitter_username") or ""
    if twitter:
        result["twitter"] = twitter

    # If no email from profile, try events API for commit emails
    if not result.get("email") and _gh_rate_ok():
        _gh_track()
        events = _fetch_json(f"https://api.github.com/users/{login}/events/public?per_page=10")
        if events and isinstance(events, list):
            for event in events:
                if event.get("type") == "PushEvent":
                    commits = event.get("payload", {}).get("commits", [])
                    for commit in commits:
                        author = commit.get("author", {})
                        cemail = author.get("email", "")
                        if cemail and "@" in cemail:
                            cemail = cemail.lower()
                            if "noreply" not in cemail and "users.noreply" not in cemail:
                                result["email"] = cemail
                                break
                    if result.get("email"):
                        break

    # If still no email but has a website, try scraping it
    if not result.get("email") and result.get("website"):
        page = _fetch_text(result["website"])
        scraped_email = extract_email_from_text(page)
        if scraped_email:
            result["email"] = scraped_email

    return result


def enrich_github_repo(repo_url):
    """Extract owner login from a GitHub repo URL and enrich."""
    if not repo_url:
        return {}
    # Parse github.com/owner/repo
    match = re.search(r'github\.com/([^/]+)', repo_url)
    if not match:
        return {}
    login = match.group(1)
    return enrich_github_user(login)


# ---------------------------------------------------------------------------
# Hacker News enrichment
# ---------------------------------------------------------------------------

def enrich_hn_user(username):
    """
    Get contact info from HN user profile.
    The 'about' field often contains email, website, twitter.
    """
    if not username:
        return {}

    result = {"profile_url": f"https://news.ycombinator.com/user?id={username}"}

    user = _fetch_json(f"https://hacker-news.firebaseio.com/v0/user/{username}.json")
    if not user:
        return result

    about = user.get("about") or ""
    if not about:
        return result

    # Extract email
    email = extract_email_from_text(about)
    if email:
        result["email"] = email

    # Extract URLs (personal websites, twitter, etc.)
    urls = extract_urls_from_text(about)
    for url in urls:
        url_lower = url.lower()
        if "twitter.com" in url_lower or "x.com" in url_lower:
            handle = url.rstrip("/").split("/")[-1]
            if handle and handle != "x.com" and handle != "twitter.com":
                result["twitter"] = handle
        elif "github.com" in url_lower:
            result["github"] = url
        elif url_lower.startswith("http"):
            # First non-social URL is likely their personal site
            if "website" not in result:
                result["website"] = url

    return result


# ---------------------------------------------------------------------------
# DEV.to enrichment
# ---------------------------------------------------------------------------

def enrich_devto_user(username):
    """
    Get contact info from DEV.to user profile API.
    Returns website, github, twitter from public profile.
    """
    if not username:
        return {}

    result = {"profile_url": f"https://dev.to/{username}"}

    user = _fetch_json(f"https://dev.to/api/users/by_username?url={username}")
    if not user:
        return result

    result["name"] = user.get("name") or username

    # DEV.to exposes these in the API
    website = user.get("website_url") or ""
    if website:
        result["website"] = website

    github = user.get("github_username") or ""
    if github:
        result["github"] = f"https://github.com/{github}"
        # Cross-enrich from GitHub if we have a username
        gh_info = enrich_github_user(github)
        if gh_info.get("email"):
            result["email"] = gh_info["email"]
        if gh_info.get("twitter") and "twitter" not in result:
            result["twitter"] = gh_info["twitter"]

    twitter = user.get("twitter_username") or ""
    if twitter:
        result["twitter"] = twitter

    # If no email from GitHub cross-check, try scraping website
    if not result.get("email") and website:
        page = _fetch_text(website)
        scraped_email = extract_email_from_text(page)
        if scraped_email:
            result["email"] = scraped_email

    return result


# ---------------------------------------------------------------------------
# Reddit enrichment (limited -- Reddit doesn't expose emails)
# ---------------------------------------------------------------------------

def enrich_reddit_user(username):
    """Reddit doesn't give us emails. Best we can do is profile URL."""
    if not username or username in ("[deleted]", "AutoModerator"):
        return {}
    return {
        "profile_url": f"https://www.reddit.com/user/{username}",
        "name": username,
    }


# ---------------------------------------------------------------------------
# Product Hunt enrichment
# ---------------------------------------------------------------------------

def enrich_producthunt_maker(user_data):
    """Extract contact from Product Hunt user data (from GraphQL response)."""
    if not user_data:
        return {}

    result = {}
    name = user_data.get("name", "")
    if name:
        result["name"] = name

    twitter = user_data.get("twitterUsername") or ""
    if twitter:
        result["twitter"] = twitter

    # PH profile image URL sometimes contains username
    profile_url = user_data.get("profileImage", "")
    if "/ph-avatars/" in profile_url:
        result["profile_url"] = f"https://www.producthunt.com/@{name.lower().replace(' ', '')}"

    return result


# ---------------------------------------------------------------------------
# Unified enrichment entry point
# ---------------------------------------------------------------------------

def enrich_contact(source, author=None, username=None, profile_data=None, source_url=None):
    """
    Main entry point. Returns a ContactInfo dict.

    Args:
        source: "github", "hacker_news", "devto", "reddit", "product_hunt"
        author: display name
        username: platform username/login
        profile_data: any extra data from the platform (e.g. PH user object)
        source_url: URL of the original post/repo

    Returns dict with:
        email, profile_url, website, twitter, github,
        needs_enrichment, contact_method
    """
    info = {
        "email": "",
        "profile_url": "",
        "website": "",
        "twitter": "",
        "github": "",
        "needs_enrichment": True,
        "contact_method": "none",
    }

    enriched = {}

    if source == "github":
        login = username or (author if author else "")
        if not login and source_url:
            match = re.search(r'github\.com/([^/]+)', source_url)
            if match:
                login = match.group(1)
        enriched = enrich_github_user(login)

    elif source == "hacker_news":
        enriched = enrich_hn_user(username or author)

    elif source == "devto":
        enriched = enrich_devto_user(username or author)

    elif source == "reddit":
        enriched = enrich_reddit_user(username or author)

    elif source == "product_hunt":
        enriched = enrich_producthunt_maker(profile_data or {})
        # Try twitter-based website lookup
        if enriched.get("twitter") and not enriched.get("email"):
            # Can't get email from twitter, but record the handle
            pass

    # Merge enriched data into info
    for key in ("email", "profile_url", "website", "twitter", "github"):
        if enriched.get(key):
            info[key] = enriched[key]

    # If we got a real email, mark as enriched
    if info["email"]:
        info["needs_enrichment"] = False
        info["contact_method"] = "email"
    elif info["profile_url"] or info["website"] or info["twitter"] or info["github"]:
        info["needs_enrichment"] = True
        info["contact_method"] = "profile"
    else:
        info["needs_enrichment"] = True
        info["contact_method"] = "none"

    return info


def build_dedup_key(source, identifier):
    """
    Build a dedup key for checking if we already have this lead/offer.
    Uses source_url or a source-specific key instead of placeholder email.

    Returns a string that can be stored in raw_data["dedup_key"].
    """
    return f"{source}:{identifier}"
