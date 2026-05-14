#!/usr/bin/env python3
"""
syncthing_pair_patch.py -- Patch a Syncthing config.xml to pair two devices
on the shared 'everlight-workspace' folder. Idempotent: safe to re-run.

Usage:
  python3 syncthing_pair_patch.py \
      --config <path/to/config.xml> \
      --folder-path <local workspace path> \
      --peer-id <peer device ID> \
      --peer-name <peer name> \
      --peer-addr <tcp://ip:22000>

Run once on each device with the OTHER device as the peer.
Works for both Syncthing v1 (config version ~37) and v2 (config version ~38+).
"""
from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET

FOLDER_ID = "everlight-workspace"
FOLDER_LABEL = "Everlight Workspace"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--folder-path", required=True)
    ap.add_argument("--peer-id", required=True)
    ap.add_argument("--peer-name", required=True)
    ap.add_argument("--peer-addr", required=True)
    args = ap.parse_args()

    tree = ET.parse(args.config)
    root = tree.getroot()

    # ---- 1. Find or create the everlight-workspace folder ----
    folder = None
    for f in root.findall("folder"):
        if f.get("id") in (FOLDER_ID, "default"):
            folder = f
            break
    if folder is None:
        folder = ET.SubElement(root, "folder")
        # minimal sane defaults; Syncthing fills the rest on load
        folder.set("type", "sendreceive")
        folder.set("rescanIntervalS", "3600")
        folder.set("fsWatcherEnabled", "true")
        folder.set("fsWatcherDelayS", "10")

    folder.set("id", FOLDER_ID)
    folder.set("label", FOLDER_LABEL)
    folder.set("path", args.folder_path)
    folder.set("ignorePerms", "true")  # sdcard/cross-fs: don't sync perms

    # ---- 2. Find this device's own ID (the <device> at config root) ----
    root_devices = root.findall("device")
    self_ids = [d.get("id") for d in root_devices]

    # ---- 3. Add peer device at config root if missing ----
    if args.peer_id not in self_ids:
        dev = ET.SubElement(root, "device")
        dev.set("id", args.peer_id)
        dev.set("name", args.peer_name)
        dev.set("compression", "metadata")
        dev.set("introducer", "false")
        addr = ET.SubElement(dev, "address")
        addr.text = args.peer_addr
        # also keep dynamic as fallback
        addr2 = ET.SubElement(dev, "address")
        addr2.text = "dynamic"
        paused = ET.SubElement(dev, "paused")
        paused.text = "false"
        print(f"  + added peer device {args.peer_name} ({args.peer_id[:7]}...)")
    else:
        # update address if device already present
        for d in root_devices:
            if d.get("id") == args.peer_id:
                # clear old addresses, set fresh
                for a in d.findall("address"):
                    d.remove(a)
                a1 = ET.SubElement(d, "address")
                a1.text = args.peer_addr
                a2 = ET.SubElement(d, "address")
                a2.text = "dynamic"
                print(f"  ~ updated peer device {args.peer_name} address")

    # ---- 4. Share the folder with the peer (add <device> under <folder>) ----
    folder_device_ids = [d.get("id") for d in folder.findall("device")]
    if args.peer_id not in folder_device_ids:
        fd = ET.SubElement(folder, "device")
        fd.set("id", args.peer_id)
        fd.set("introducedBy", "")
        print(f"  + shared '{FOLDER_ID}' with {args.peer_name}")
    # ensure self is also in the folder's device list
    for sid in self_ids:
        if sid and sid not in folder_device_ids and sid != args.peer_id:
            fd = ET.SubElement(folder, "device")
            fd.set("id", sid)
            fd.set("introducedBy", "")

    tree.write(args.config, encoding="UTF-8", xml_declaration=False)
    print(f"  wrote {args.config}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
