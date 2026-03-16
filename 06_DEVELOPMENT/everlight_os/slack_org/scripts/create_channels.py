#!/usr/bin/env python3
"""Create or connect Slack channels from channel_map.json."""

from __future__ import annotations

import argparse
import sys
from typing import Dict

from everlight_os.slack_org.channel_registry import ChannelRegistry
from everlight_os.slack_org.config import SlackOrgConfig
from everlight_os.slack_org.slack_api import SlackApiClient, SlackApiError


def _collect_existing_channels(api: SlackApiClient) -> Dict[str, dict]:
    by_name: Dict[str, dict] = {}
    cursor = ""
    while True:
        data = api.conversations_list(cursor=cursor)
        for channel in data.get("channels", []):
            name = (channel.get("name") or "").strip()
            if name:
                by_name[name] = channel
        cursor = (((data.get("response_metadata") or {}).get("next_cursor")) or "").strip()
        if not cursor:
            break
    return by_name


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--private",
        action="store_true",
        help="Create missing channels as private channels.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions only (no API mutations).",
    )
    args = parser.parse_args()

    config = SlackOrgConfig.from_env()
    if args.dry_run:
        config.dry_run = True

    registry = ChannelRegistry(
        channel_map_path=config.channel_map_path,
        registry_path=config.channel_registry_path,
    )

    if config.dry_run:
        print("Dry run enabled. Channels from map:")
        for name in registry.all_channel_names():
            print(f"  - {name}")
        print(f"Would update registry at: {config.channel_registry_path}")
        return 0

    api = SlackApiClient(config)

    if not config.bot_token:
        print("Missing SLACK_BOT_TOKEN. Set it in env before running this script.")
        return 2

    try:
        existing_by_name = _collect_existing_channels(api)
    except SlackApiError as exc:
        print(f"Failed loading Slack channels: {exc}")
        return 3

    created = []
    connected = []
    failed = []

    for name in registry.all_channel_names():
        channel = existing_by_name.get(name)
        if channel:
            registry.set_channel_id(name, channel.get("id", ""))
            connected.append(name)
            continue

        try:
            resp = api.conversations_create(name=name, is_private=args.private)
            channel_data = resp.get("channel", {}) if isinstance(resp, dict) else {}
            channel_id = channel_data.get("id", "")
            if channel_id:
                registry.set_channel_id(name, channel_id)
                created.append(name)
            else:
                failed.append((name, "missing_channel_id"))
        except SlackApiError as exc:
            # Name can still exist if Slack race/visibility issue; retry by re-listing once.
            if "name_taken" in str(exc):
                try:
                    refreshed = _collect_existing_channels(api)
                    channel = refreshed.get(name)
                    if channel:
                        registry.set_channel_id(name, channel.get("id", ""))
                        connected.append(name)
                        continue
                except Exception:  # noqa: BLE001
                    pass
            failed.append((name, str(exc)))

    registry.save()

    print(f"Connected channels: {len(connected)}")
    for name in connected:
        print(f"  = {name}")
    print(f"Created channels: {len(created)}")
    for name in created:
        print(f"  + {name}")
    print(f"Failed channels: {len(failed)}")
    for name, reason in failed:
        print(f"  ! {name} -> {reason}")
    print(f"Registry path: {config.channel_registry_path}")

    return 0 if not failed else 4


if __name__ == "__main__":
    sys.exit(main())
