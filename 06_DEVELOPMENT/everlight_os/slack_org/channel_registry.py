"""Channel map + id registry helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


def _normalize_channel_name(name: str) -> str:
    clean = name.strip()
    if clean.startswith("#"):
        clean = clean[1:]
    return clean


def _flatten_channel_map(node: object, prefix: str = "") -> List[Tuple[str, str]]:
    items: List[Tuple[str, str]] = []
    if isinstance(node, dict):
        for key, value in node.items():
            child_prefix = f"{prefix}.{key}" if prefix else key
            items.extend(_flatten_channel_map(value, child_prefix))
    elif isinstance(node, str):
        items.append((prefix, _normalize_channel_name(node)))
    return items


class ChannelRegistry:
    """Loads channel names from map and stores resolved Slack channel ids."""

    def __init__(self, channel_map_path: Path, registry_path: Path):
        self.channel_map_path = channel_map_path
        self.registry_path = registry_path
        self._channel_map = self._load_channel_map()
        self._key_to_name = dict(_flatten_channel_map(self._channel_map))
        self._name_to_id = self._load_registry()

    def _load_channel_map(self) -> Dict[str, object]:
        with self.channel_map_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _load_registry(self) -> Dict[str, str]:
        if not self.registry_path.exists():
            return {}
        with self.registry_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return {k: v for k, v in data.items() if isinstance(k, str) and isinstance(v, str)}

    def save(self) -> None:
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        with self.registry_path.open("w", encoding="utf-8") as f:
            json.dump(self._name_to_id, f, indent=2, sort_keys=True)
            f.write("\n")

    @property
    def channel_map(self) -> Dict[str, object]:
        return self._channel_map

    def all_channel_names(self) -> List[str]:
        unique = sorted(set(self._key_to_name.values()))
        return unique

    def get_channel_name(self, key_or_name: str) -> str:
        direct_key = key_or_name.strip()
        if direct_key in self._key_to_name:
            return self._key_to_name[direct_key]
        return _normalize_channel_name(direct_key)

    def get_channel_id(self, key_or_name: str) -> str:
        name = self.get_channel_name(key_or_name)
        return self._name_to_id.get(name, "")

    def set_channel_id(self, key_or_name: str, channel_id: str) -> None:
        name = self.get_channel_name(key_or_name)
        self._name_to_id[name] = channel_id

    def has_channel_id(self, key_or_name: str) -> bool:
        return bool(self.get_channel_id(key_or_name))

    def resolve_channel_ref(self, key_or_name: str) -> str:
        """Resolve key/name/id to Slack channel id where possible."""
        value = key_or_name.strip()
        if value.startswith(("C", "G")) and len(value) >= 9:
            return value
        existing = self.get_channel_id(value)
        if existing:
            return existing
        return ""

    def find_errors_channel_key(self) -> str:
        for key, name in self._key_to_name.items():
            if name == "agent-errors":
                return key
        return "shared_ops.errors"

    def ingest_existing_channels(self, channels: Iterable[dict]) -> None:
        for channel in channels:
            name = _normalize_channel_name(channel.get("name", ""))
            cid = channel.get("id", "")
            if name and cid:
                self._name_to_id[name] = cid

