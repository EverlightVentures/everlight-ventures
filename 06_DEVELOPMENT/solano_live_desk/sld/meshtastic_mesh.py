from __future__ import annotations

import base64
import json
import os
import threading
import time

# Read the Meshtastic mesh hardware-free via the public MQTT bridge. Nodes that
# uplink to mqtt.meshtastic.org are decodable on the default channel (well-known
# key). We keep only nodes inside the operator's bubble, rotated hourly.

_KEY = base64.b64decode("1PG7OiApB1nwvP+rz05pAQ==")  # expanded default-channel PSK (AQ==)
# Subscribe to all California mesh topics; the lat/lon bubble filter keeps only
# nodes within the operator's radius (topic naming is inconsistent, so filter by
# position, not by topic).
NORCAL_TOPICS = ["msh/US/CA/#"]


def _decrypt(pkt) -> bytes | None:
    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

        frm = getattr(pkt, "from")
        nonce = pkt.id.to_bytes(8, "little") + frm.to_bytes(8, "little")
        c = Cipher(algorithms.AES(_KEY), modes.CTR(nonce)).decryptor()
        return c.update(pkt.encrypted) + c.finalize()
    except Exception:  # noqa: BLE001
        return None


class MeshCollector:
    def __init__(self, base: str, radius_mi: float = 45.0):
        self.base = base
        self.radius = radius_mi
        self.nodes: dict[str, dict] = {}
        self.msgs: list[dict] = []
        self.lock = threading.Lock()

    def _center(self):
        try:
            d = json.loads(open(os.path.join(self.base, "last_location.json")).read())
            return (float(d["lat"]), float(d["lon"]))
        except Exception:  # noqa: BLE001
            return (38.25, -122.04)

    def _in_bubble(self, lat, lon) -> bool:
        from .geo_county import distance_mi

        return distance_mi(self._center(), (lat, lon)) <= self.radius

    def on_msg(self, client, userdata, m):
        try:
            from meshtastic import mesh_pb2, mqtt_pb2, portnums_pb2

            env = mqtt_pb2.ServiceEnvelope()
            env.ParseFromString(m.payload)
            p = env.packet
            nid = f"!{getattr(p, 'from'):08x}"
            raw = p.decoded.payload if p.HasField("decoded") else _decrypt(p)
            if raw is None:
                return
            data = p.decoded if p.HasField("decoded") else mesh_pb2.Data.FromString(raw)
            now = time.time()
            if data.portnum == portnums_pb2.POSITION_APP:
                pos = mesh_pb2.Position.FromString(data.payload)
                if pos.latitude_i:
                    lat, lon = pos.latitude_i / 1e7, pos.longitude_i / 1e7
                    if self._in_bubble(lat, lon):
                        with self.lock:
                            n = self.nodes.setdefault(nid, {"id": nid})
                            n.update({"lat": lat, "lon": lon, "last_seen": now})
            elif data.portnum == portnums_pb2.NODEINFO_APP:
                ui = mesh_pb2.User.FromString(data.payload)
                with self.lock:
                    n = self.nodes.setdefault(nid, {"id": nid})
                    n["name"] = ui.long_name or ui.short_name
                    n["last_seen"] = now
            elif data.portnum == portnums_pb2.TEXT_MESSAGE_APP:
                txt = data.payload.decode("utf-8", "ignore")
                with self.lock:
                    node = self.nodes.get(nid) or {}
                    if node.get("lat") is not None:  # only messages from placed nodes
                        self.msgs.append({"id": nid, "name": node.get("name"), "text": txt,
                                          "lat": node.get("lat"), "lon": node.get("lon"), "at": now})
                        self.msgs = self.msgs[-40:]
        except Exception:  # noqa: BLE001
            pass

    def snapshot(self) -> dict:
        now = time.time()
        with self.lock:
            self.nodes = {k: v for k, v in self.nodes.items() if now - v.get("last_seen", 0) < 3600}
            nodes = [v for v in self.nodes.values() if "lat" in v]
            msgs = [x for x in self.msgs if now - x["at"] < 3600]
        return {"nodes": nodes, "messages": msgs, "updated": int(now)}

    def write(self):
        try:
            json.dump(self.snapshot(), open(os.path.join(self.base, "mesh.json"), "w"))
        except Exception:  # noqa: BLE001
            pass

    def run(self):
        import paho.mqtt.client as mqtt

        try:
            cl = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        except Exception:  # noqa: BLE001
            cl = mqtt.Client()
        cl.username_pw_set("meshdev", "large4cats")
        cl.on_connect = lambda c, u, f, rc, props=None: [c.subscribe(t) for t in NORCAL_TOPICS]
        cl.on_message = self.on_msg
        cl.connect("mqtt.meshtastic.org", 1883, 30)
        cl.loop_start()
        while True:
            time.sleep(10)
            self.write()
