#!/usr/bin/env python3
"""Standalone Meshtastic collector: subscribes to the public MQTT, decodes mesh
nodes/messages inside the operator's bubble, writes store/mesh.json. Its own
process so the MQTT + protobuf load never touches the API."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sld import config  # noqa: E402

config.load_env()
from sld.meshtastic_mesh import MeshCollector  # noqa: E402

base = os.environ.get("SLD_STORE", os.path.join(os.path.dirname(__file__), "..", "store"))
radius = float(os.environ.get("SLD_RADIUS_MI", "45"))
print(f"[mesh] collecting Meshtastic within {radius}mi -> {base}/mesh.json", flush=True)
MeshCollector(base, radius).run()
