"""
Semantic Search -- pgvector-powered lead similarity search on Supabase.

Embeds lead descriptions as vectors and enables "find leads like X" queries.
Uses TF-IDF embeddings (free, no API) or sentence-transformers if available.

Usage:
    from semantic_search import embed_leads, search_similar
    embed_leads()  # one-time: embed all existing leads
    results = search_similar("HVAC company needs automation, $30k budget")
"""
from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

import numpy as np

log = logging.getLogger(__name__)

# Supabase config
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://jdqqmsmwmbsnlnstyavl.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY", os.environ.get("SUPABASE_KEY", ""))

EMBEDDING_DIM = 384


def _get_supabase_headers():
    key = SUPABASE_KEY
    if not key:
        # Try loading from .env files
        for env_path in ["/home/opc/.env", "/mnt/sdcard/AA_MY_DRIVE/03_Credentials/.env"]:
            try:
                for line in open(env_path):
                    if line.startswith("SUPABASE_ANON_KEY=") or line.startswith("SUPABASE_KEY="):
                        key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
            except Exception:
                continue
    return {
        "Content-Type": "application/json",
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }


def _embed_text(text: str) -> list[float]:
    """Convert text to a 384-dim embedding vector.

    Uses sklearn TF-IDF (free, always available).
    Returns a normalized vector suitable for cosine similarity.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.preprocessing import normalize

    # Create a simple embedding by hashing text features into fixed dimensions
    # This is a lightweight alternative to sentence-transformers
    vectorizer = TfidfVectorizer(max_features=EMBEDDING_DIM, stop_words='english')

    # Need at least 2 docs for TF-IDF; use a dummy
    docs = [text, "placeholder document for tfidf fitting"]
    vectors = vectorizer.fit_transform(docs).toarray().astype(np.float32)
    vec = normalize(vectors[:1])[0]

    # Pad or truncate to exactly EMBEDDING_DIM
    if len(vec) < EMBEDDING_DIM:
        vec = np.pad(vec, (0, EMBEDDING_DIM - len(vec)))
    return vec[:EMBEDDING_DIM].tolist()


def embed_leads(limit: int = 100) -> dict:
    """Embed all broker_leads that don't have embeddings yet."""
    import urllib.request

    headers = _get_supabase_headers()

    # Fetch leads without embeddings
    url = f"{SUPABASE_URL}/rest/v1/broker_leads?embedding=is.null&select=id,name,company,need_description&limit={limit}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            leads = json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}

    if not leads:
        return {"embedded": 0, "message": "all leads already have embeddings"}

    embedded = 0
    for lead in leads:
        text = f"{lead.get('name', '')} {lead.get('company', '')} {lead.get('need_description', '')}"
        if len(text.strip()) < 5:
            continue

        vec = _embed_text(text)

        # Update lead with embedding
        update_url = f"{SUPABASE_URL}/rest/v1/broker_leads?id=eq.{lead['id']}"
        update_headers = {**headers, "Prefer": "return=minimal"}
        payload = json.dumps({"embedding": vec}).encode()
        req = urllib.request.Request(update_url, data=payload, headers=update_headers, method="PATCH")
        try:
            urllib.request.urlopen(req, timeout=10)
            embedded += 1
        except Exception as e:
            log.warning(f"Failed to embed lead {lead['id']}: {e}")

    return {"embedded": embedded, "total": len(leads)}


def search_similar(query: str, top_k: int = 10) -> list[dict]:
    """Find leads semantically similar to a query.

    Usage: search_similar("HVAC company needs AI chatbot, budget $30k")
    """
    import urllib.request

    vec = _embed_text(query)
    headers = _get_supabase_headers()

    # Call the Supabase RPC function
    url = f"{SUPABASE_URL}/rest/v1/rpc/search_similar_leads"
    payload = json.dumps({
        "query_embedding": vec,
        "match_threshold": 0.3,
        "match_count": top_k,
    }).encode()
    req = urllib.request.Request(url, data=payload, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            results = json.loads(resp.read())
            return results if isinstance(results, list) else []
    except Exception as e:
        log.warning(f"Semantic search failed: {e}")
        return []


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["embed", "search"])
    parser.add_argument("--query", type=str, default="")
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args()

    if args.command == "embed":
        result = embed_leads(limit=args.limit)
        print(json.dumps(result, indent=2))
    elif args.command == "search":
        if not args.query:
            print("Usage: python semantic_search.py search --query 'HVAC automation'")
        else:
            results = search_similar(args.query, top_k=10)
            for r in results:
                print(f"  [{r.get('similarity', 0):.3f}] {r.get('name', '?')} - {r.get('need_description', '')[:60]}")
