"""pty_bridge.py -- minimal stdlib WebSocket + PTY pump for the Lucrex deck.

Runs a real shell / Claude inside a pty and streams it over one WebSocket.
No third-party deps: the WebSocket handshake and frame codec are hand-rolled on
hashlib/base64/struct so this works on the phone's proot (no pip, no npm).
"""
from __future__ import annotations
import base64, fcntl, hashlib, json, os, pty, select, signal, struct, termios

WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


def accept_key(client_key):
    """Compute the Sec-WebSocket-Accept response value (RFC 6455)."""
    h = hashlib.sha1((client_key + WS_GUID).encode()).digest()
    return base64.b64encode(h).decode()


def encode_frame(payload, opcode=0x1):
    """Server -> client frame (never masked). opcode 0x1 text, 0x2 binary."""
    b0 = 0x80 | (opcode & 0x0f)
    n = len(payload)
    if n < 126:
        header = struct.pack("!BB", b0, n)
    elif n < (1 << 16):
        header = struct.pack("!BBH", b0, 126, n)
    else:
        header = struct.pack("!BBQ", b0, 127, n)
    return header + payload


def mask_frame(payload, opcode=0x1):
    """Build a masked client -> server frame. Used by tests to simulate a browser."""
    b0 = 0x80 | (opcode & 0x0f)
    n = len(payload)
    mask = b"\xa1\xb2\xc3\xd4"
    if n < 126:
        header = struct.pack("!BB", b0, 0x80 | n)
    elif n < (1 << 16):
        header = struct.pack("!BBH", b0, 0x80 | 126, n)
    else:
        header = struct.pack("!BBQ", b0, 0x80 | 127, n)
    masked = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    return header + mask + masked


def decode_frames(buf):
    """Decode as many complete frames as `buf` holds.

    Returns (list_of_(opcode, payload), leftover_bytes). Incomplete trailing
    frames are returned as leftover so the caller can prepend the next read.
    """
    msgs = []
    i = 0
    L = len(buf)
    while True:
        if L - i < 2:
            break
        b0, b1 = buf[i], buf[i + 1]
        opcode = b0 & 0x0f
        masked = b1 & 0x80
        ln = b1 & 0x7f
        j = i + 2
        if ln == 126:
            if L - j < 2:
                break
            ln = struct.unpack("!H", buf[j:j + 2])[0]
            j += 2
        elif ln == 127:
            if L - j < 8:
                break
            ln = struct.unpack("!Q", buf[j:j + 8])[0]
            j += 8
        mask = b""
        if masked:
            if L - j < 4:
                break
            mask = buf[j:j + 4]
            j += 4
        if L - j < ln:
            break
        data = buf[j:j + ln]
        j += ln
        if masked:
            data = bytes(b ^ mask[k % 4] for k, b in enumerate(data))
        msgs.append((opcode, data))
        i = j
    return msgs, buf[i:]


def _set_winsize(fd, rows, cols):
    try:
        fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", rows, cols, 0, 0))
    except Exception:
        pass


def run_pty_session(sock, spawn, env):
    """Blocking pump. Forks a pty, execs `spawn`, bridges sock <-> pty until close."""
    pid, master = pty.fork()
    if pid == 0:  # child
        os.environ.update(env)
        try:
            os.execvp(spawn[0], spawn)
        except Exception:
            os._exit(1)
    buf = b""
    try:
        while True:
            r, _, _ = select.select([sock, master], [], [], 60)
            if master in r:
                try:
                    data = os.read(master, 65536)
                except OSError:
                    data = b""
                if not data:
                    sock.sendall(encode_frame(
                        b"\r\n[ session ended -- tap to reconnect ]\r\n"))
                    break
                sock.sendall(encode_frame(data, opcode=0x2))
            if sock in r:
                chunk = sock.recv(65536)
                if not chunk:
                    break
                buf += chunk
                frames, buf = decode_frames(buf)
                for opcode, payload in frames:
                    if opcode == 0x8:  # close
                        return
                    if opcode in (0x1, 0x2):
                        if payload[:1] == b"\x00":  # control JSON (resize), 0x00 sentinel
                            try:
                                ctl = json.loads(payload[1:].decode())
                                if ctl.get("type") == "resize":
                                    _set_winsize(master, int(ctl["rows"]),
                                                 int(ctl["cols"]))
                            except Exception:
                                pass
                        else:
                            os.write(master, payload)
    finally:
        try:
            os.kill(pid, signal.SIGKILL)
        except Exception:
            pass
        try:
            os.waitpid(pid, 0)
        except Exception:
            pass
        try:
            os.close(master)
        except Exception:
            pass
