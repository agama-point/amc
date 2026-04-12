# lib: amc/decode.py
# usage: from amc.decode import parse_packet, format_output

import hashlib
import struct
import re
import time
from datetime import datetime, timezone
from Crypto.Cipher import AES

__version__ = "0.33 | 2026-03"

# --- Output mode ---
# MSG_ONLY: if True, only print lines with successfully decrypted channel messages
MSG_ONLY = True

# Deduplication window in seconds — same (channel, text) within this window is suppressed
DEDUP_WINDOW = 3.0 # 5.0

def print_knowledge_base():
   print("="*63)
   print("""
   AMC | AGAMA_POINT MESHCORE GRP_TXT DECODER 
   ==========================================
   Algorithm: AES-128 ECB
   Key:       SHA256(channel_name)[:16]
   Struct.:   [header][path_len][path(4B)][ch_hash(3B)][enc(26B)][mac(6B)]
   Plaintext: [timestamp(4B LE)][0x00][text\x00...]
   ------------------------------------------------
   Info:
   """)
   print("   ver: ", __version__)
   print("="*63)


# --- Configuration ---

def _make_channel(name: str) -> dict:
    key = hashlib.sha256(name.encode()).digest()[:16]
    # MeshCore uses a hash of the key to identify the channel in the packet
    ch_hash = hashlib.sha256(key).digest()[0]
    return {"name": name, "key": key, "hash_byte": ch_hash}

CHANNELS = [
    _make_channel("#test"),
    _make_channel("#praha"),
    _make_channel("#2byte"),
    _make_channel("#jokes"),
    _make_channel("#tech"),
    _make_channel("#freebeer"),
    {
        "name": "Public", 
        "key": bytes.fromhex("8b3387e9c5cdea6ac9e5edbaa115cd72"),
        "hash_byte": hashlib.sha256(bytes.fromhex("8b3387e9c5cdea6ac9e5edbaa115cd72")).digest()[0]
    },
]


# MeshCore packet type codes
# BLE 0x88 wrapper structure:
#   [88][node_hi][node_lo][mesh_type][path_len][path...][payload...]
# The real MeshCore type is at raw[3].
# If raw[3] is not a known type (e.g. a relay/path byte), mark as RELAY.
_MSG_TYPES = {
    0x00: "ACK",
    0x01: "ADVERT",
    0x02: "REQUEST",
    0x03: "RESPONSE",
    0x04: "ANON REQ",
    0x05: "PATH RESP",
    0x06: "ANON RESP",
    0x08: "PATH",
    0x10: "ADVERT",
    0x11: "ADVERT",
    0x12: "ADVERT",
    0x13: "ADVERT",
    0x15: "CHAN MSG",
    0x16: "CHAN MSG",
    0x40: "TRACE REQ",
    0x41: "TRACE RESP",
    0x80: "ACK",
    0x83: "ACK",
}

def _get_msg_type(raw: bytes) -> str:
    """
    Detect MeshCore message type from BLE notification.

    BLE 0x88 wrapper structure (standard):
      [88][node_hi][node_lo][mesh_type][path_len][path...][payload...]

    During the 1B→2B node ID transition, some packets carry an extra
    relay/path byte at offset 3, pushing the real type to offset 4.
    Heuristic: if raw[3] is a known type → use it; otherwise → RELAY.

    For non-0x88 outer types (0x80, 0x83, 0x8E...) use raw[0] directly.
    """
    if not raw:
        return "?"
    p_type = raw[0]
    if p_type == 0x88:
        if len(raw) >= 4:
            candidate = raw[3]
            if candidate in _MSG_TYPES:
                return _MSG_TYPES[candidate]
            return "RELAY"
        return "?"
    return _MSG_TYPES.get(p_type, f"?{p_type:02X}")


def try_decrypt_payload(data: bytes) -> dict | None:
    if len(data) < 32:
        return None
    
    num_blocks = min(len(data) // 16, 6)
    payload = data[:num_blocks * 16]

    for ch in CHANNELS:
        try:
            cipher = AES.new(ch["key"], AES.MODE_ECB)
            dec = b"".join(cipher.decrypt(payload[i*16:(i+1)*16]) for i in range(num_blocks))
            
            # 1. TIMESTAMP VALIDATION (2025–2027)
            ts = struct.unpack("<I", dec[0:4])[0]
            if not (1735689600 < ts < 1861910400):
                continue

            # 2. CHANNEL HASH VALIDATION (key filter against noise)
            ch_byte = dec[4]
            
            # 3. TEXT DECODING
            for start in [5, 4]:  # try both common offsets
                raw_text = dec[start:].split(b'\x00')[0]
                if len(raw_text) < 2:
                    continue
                
                try:
                    text = raw_text.decode("utf-8", errors="strict")
                    
                    # Filter out nonsensical characters
                    if not all(ord(c) < 1000 for c in text):
                        continue 
                    
                    # If channel is public or hash matches, we have a hit
                    if ch["name"] == "public" or ch_byte == ch["hash_byte"] or text.isprintable():
                        return {
                            "channel": ch["name"],
                            "text": text,
                            "ts": ts
                        }
                except:
                    continue
        except:
            continue
    return None


def parse_packet(raw: bytes) -> dict:
    p_type = raw[0] if raw else 0
    res = {
        "type": f"{p_type:02X}",
        "msg_type": _get_msg_type(raw),
        "len": len(raw),
        "raw": raw.hex().upper(),
        "route": None,
        "decrypted": None,
        "plain_text": None
    }

    if p_type == 0x88 and len(raw) >= 5:
        res["route"] = f"{raw[1:3].hex().upper()} ➔ {raw[3:5].hex().upper()}"

    # Scan only logical starting points (offset 0–16) to reduce false positives
    for offset in range(min(len(raw) - 31, 20)):
        found = try_decrypt_payload(raw[offset:])
        if found:
            res["decrypted"] = found
            break

    # Plain-text for Node Info (beacons with node names)
    if not res["decrypted"]:
        pattern = b'[a-zA-Z0-9\\s\\.\\/\\-\\[\\]\\:\\@\\_\\?\\!]{7,}'
        match = re.search(pattern, raw)
        if match:
            try:
                text = match.group(0).decode("utf-8", errors="ignore").strip()
                if len(text) > 7:
                    res["plain_text"] = text
            except:
                pass

    return res


# --- Deduplication state ---
# key: (channel, text) → last seen wall-clock time
_seen: dict[tuple, float] = {}

def _is_duplicate(channel: str, text: str) -> bool:
    """Return True if this (channel, text) was already seen within DEDUP_WINDOW seconds."""
    key = (channel, text)
    now = time.monotonic()
    last = _seen.get(key)
    if last is not None and (now - last) < DEDUP_WINDOW:
        return True
    _seen[key] = now
    # Evict old entries occasionally to avoid unbounded growth
    if len(_seen) > 500:
        cutoff = now - DEDUP_WINDOW
        for k in [k for k, v in _seen.items() if v < cutoff]:
            del _seen[k]
    return False


def format_output(p: dict, debug_mode: bool = False) -> str | None:
    """
    Format a parsed packet for output.
    Returns None if the packet should be suppressed (MSG_ONLY or duplicate).
    """
    d = p.get("decrypted")

    # MSG_ONLY: suppress everything without a decrypted message
    if MSG_ONLY and not d:
        return None

    # Deduplication: suppress repeated relays of the same message
    if d and _is_duplicate(d["channel"], d["text"]):
        return None

    now = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    route_part = f" | {p['route']}" if p['route'] else ""
    msg_type_part = f" | {p['msg_type']}"
    header = f"{now} | {p['type']} | {p['len']}B{route_part}{msg_type_part}"
    lines = [header]

    if debug_mode:
        lines.append(f"  RAW: {p['raw']}")

    if d:
        # Green output for successfully decrypted channel messages
        lines.append(f"  \033[92m[{d['channel']}] {d['text']}\033[0m")
    elif p["plain_text"]:
        # Cyan output for captured plain text (beacons/node info)
        lines.append(f"  \033[96mINFO: {p['plain_text']}\033[0m")

    return "\n".join(lines)