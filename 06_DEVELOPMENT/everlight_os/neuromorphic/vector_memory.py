"""
Vector Memory -- FAISS-powered similarity search for agent memory.

Augments Blinko RAG with fast local vector search. Agents can store
and retrieve context by semantic similarity rather than keyword matching.

Uses: FAISS (Facebook AI Similarity Search) -- free, open source, BSD license.
Embeddings: TF-IDF based (no API needed).
Storage: JSON serialization (safe, no pickle).
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

log = logging.getLogger(__name__)

STATE_DIR = Path(__file__).parent / "state"
STATE_DIR.mkdir(exist_ok=True)


class VectorMemory:
    """FAISS-powered vector memory for Hive agents.

    Stores text entries with metadata, indexes them as TF-IDF vectors,
    and enables fast similarity search. No external API needed.

    Usage:
        mem = VectorMemory("rex_memory")
        mem.add("BTC breaking 70k resistance, XLM correlated", {"source": "market"})
        mem.add("Lead from Portland HVAC company, $30k budget", {"source": "broker"})
        results = mem.search("crypto market correlation", top_k=3)
    """

    def __init__(self, name: str = "hive_memory", dim: int = 512):
        self.name = name
        self.dim = dim
        self.entries: list[dict] = []
        self.vectorizer = TfidfVectorizer(max_features=dim, stop_words='english')
        self.index: faiss.IndexFlatIP | None = None
        self._is_fitted = False
        self._load()

    def add(self, text: str, metadata: dict | None = None):
        """Add a memory entry."""
        self.entries.append({
            "text": text,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat(),
            "id": len(self.entries),
        })
        if len(self.entries) >= 5:
            self._rebuild_index()

    def add_batch(self, items: list[dict]):
        """Add multiple entries. Each dict needs 'text' key."""
        for item in items:
            self.entries.append({
                "text": item["text"],
                "metadata": item.get("metadata", {}),
                "timestamp": datetime.utcnow().isoformat(),
                "id": len(self.entries),
            })
        if len(self.entries) >= 5:
            self._rebuild_index()

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Find the most similar memories to a query."""
        if not self._is_fitted or self.index is None or len(self.entries) < 5:
            return self._substring_search(query, top_k)

        query_vec = self.vectorizer.transform([query]).toarray().astype(np.float32)
        query_vec = normalize(query_vec)
        k = min(top_k, len(self.entries))
        scores, indices = self.index.search(query_vec, k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.entries):
                continue
            entry = self.entries[idx].copy()
            entry["similarity"] = float(score)
            results.append(entry)
        return results

    def _substring_search(self, query: str, top_k: int) -> list[dict]:
        """Fallback search when FAISS index isn't ready."""
        query_words = set(query.lower().split())
        scored = []
        for entry in self.entries:
            text_words = set(entry["text"].lower().split())
            overlap = len(query_words & text_words)
            if overlap > 0:
                scored.append((overlap / max(len(query_words), 1), entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [{"similarity": s, **e} for s, e in scored[:top_k]]

    def _rebuild_index(self):
        """Rebuild FAISS index from all entries."""
        texts = [e["text"] for e in self.entries]
        try:
            vectors = self.vectorizer.fit_transform(texts).toarray().astype(np.float32)
            vectors = normalize(vectors)
            self.index = faiss.IndexFlatIP(vectors.shape[1])
            self.index.add(vectors)
            self._is_fitted = True
        except Exception as e:
            log.warning(f"FAISS index rebuild failed: {e}")

    def save(self):
        """Persist memory to disk as JSON (safe serialization)."""
        path = STATE_DIR / f"{self.name}_memory.json"
        path.write_text(json.dumps(self.entries, indent=2, default=str))

    def _load(self):
        """Load memory from disk."""
        path = STATE_DIR / f"{self.name}_memory.json"
        if path.exists():
            try:
                self.entries = json.loads(path.read_text())
                if len(self.entries) >= 5:
                    self._rebuild_index()
                log.info(f"Loaded {len(self.entries)} memories for {self.name}")
            except Exception as e:
                log.warning(f"Memory load failed for {self.name}: {e}")

    def get_stats(self) -> dict:
        return {
            "name": self.name,
            "entries": len(self.entries),
            "indexed": self._is_fitted,
            "index_size": self.index.ntotal if self.index else 0,
        }


_memories: dict[str, VectorMemory] = {}


def get_memory(agent_name: str = "hive") -> VectorMemory:
    """Get or create a vector memory for an agent."""
    if agent_name not in _memories:
        _memories[agent_name] = VectorMemory(name=agent_name)
    return _memories[agent_name]
