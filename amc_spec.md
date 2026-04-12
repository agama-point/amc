# MeshCore Protocol — AGAMA Point Integration Specification

> \*\*AMC | AGAMA\_POINT MESHCORE decoder\*\* — internal reference for how raw frames are extracted, parsed, and decrypted from the MeshCore transport layer.

\---

## Table of Contents

1. [Overview](#overview)
2. [Transport Layer — RAW Hex Extraction](#transport-layer--raw-hex-extraction)
3. [Frame Structure](#frame-structure)
4. [Message Type Registry](#message-type-registry)
5. [Channel Message Decryption (GRP\_TXT)](#channel-message-decryption-grp_txt)
6. [Full Parsing Pipeline](#full-parsing-pipeline)
7. [Field Reference](#field-reference)
8. [Notes \& Edge Cases](#notes--edge-cases)

\---

## Overview

MeshCore is a LoRa-based mesh networking protocol. Nodes exchange binary frames over a radio transport. AGAMA Point intercepts these frames at the transport boundary, extracts raw hex payloads wrapped in the `0x88` marker, and decodes them into structured messages — including decrypting AES-128 ECB group channel text.

```
\[Radio RX] → \[Transport Layer 0x88 wrapper] → \[RAW hex] → \[Frame parser] → \[Decryptor] → \[Decoded message]
```

\---

## Transport Layer — RAW Hex Extraction

Frames arrive wrapped in the MeshCore transport envelope. The outer wrapper is identified by the leading byte `0x88`, which signals a MeshCore radio frame.

### Extraction procedure

```python
def extract\_raw(transport\_bytes: bytes) -> bytes | None:
    """
    Strip the transport wrapper (0x88...) and return the inner payload.
    Returns None if the frame does not match the expected wrapper.
    """
    if len(transport\_bytes) < 2:
        return None
    if transport\_bytes\[0] != 0x88:
        return None
    # Remaining bytes after the wrapper marker are the raw frame
    return transport\_bytes\[1:]
```

The `0x88`-prefixed frames are the only ones forwarded to the parser. All other transport markers are silently dropped.

\---

## Frame Structure

After stripping the transport wrapper, the raw frame has the following binary layout:

```
Offset  Size    Field
──────────────────────────────────────────────────────
0       1 B     msg\_type       — message type byte (see registry below)
1       1 B     path\_len       — number of hops in path (0–N)
2       4 B     path           — last 4 bytes of path node IDs (fixed size)
6       3 B     ch\_hash        — first 3 bytes of SHA-256(channel\_name)
9       26 B    enc\_payload    — AES-128 ECB encrypted payload
35      6 B     mac            — message authentication / sender fingerprint
──────────────────────────────────────────────────────
Total:  41 B    (minimum for a CHAN MSG frame)
```

### Struct layout (Python)

```python
import struct

FRAME\_HEADER\_FMT = "<BB"   # msg\_type (u8), path\_len (u8)
PATH\_SIZE        = 4       # bytes
CH\_HASH\_SIZE     = 3       # bytes
ENC\_SIZE         = 26      # bytes
MAC\_SIZE         = 6       # bytes

def parse\_frame\_header(raw: bytes) -> dict:
    if len(raw) < 2 + PATH\_SIZE + CH\_HASH\_SIZE + ENC\_SIZE + MAC\_SIZE:
        raise ValueError(f"Frame too short: {len(raw)} bytes")

    msg\_type, path\_len = struct.unpack\_from(FRAME\_HEADER\_FMT, raw, 0)
    offset = 2
    path     = raw\[offset : offset + PATH\_SIZE];   offset += PATH\_SIZE
    ch\_hash  = raw\[offset : offset + CH\_HASH\_SIZE]; offset += CH\_HASH\_SIZE
    enc      = raw\[offset : offset + ENC\_SIZE];     offset += ENC\_SIZE
    mac      = raw\[offset : offset + MAC\_SIZE];     offset += MAC\_SIZE

    return {
        "msg\_type": msg\_type,
        "path\_len": path\_len,
        "path":     path.hex(),
        "ch\_hash":  ch\_hash.hex(),
        "enc":      enc.hex(),
        "mac":      mac.hex(),
    }
```

\---

## Message Type Registry

All known `msg\_type` values currently observed in the wild:

```python
\_MSG\_TYPES = {
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
    0x15: "CHAN MSG",    # ← group channel message (encrypted)
    0x16: "CHAN MSG",    # ← group channel message (variant)
    0x40: "TRACE REQ",
    0x41: "TRACE RESP",
    0x80: "ACK",
    0x83: "ACK",
}

def msg\_type\_name(byte: int) -> str:
    return \_MSG\_TYPES.get(byte, f"UNKNOWN(0x{byte:02X})")
```

> \*\*Note:\*\* Types `0x15` and `0x16` are the only ones that carry an encrypted group text payload. All other types are control/routing frames and do not require decryption.

\---

## Channel Message Decryption (GRP\_TXT)

```
AMC | AGAMA\_POINT MESHCORE GRP\_TXT DECODER
==========================================
Algorithm: AES-128 ECB
Key:       SHA256(channel\_name)\[:16]
Struct.:   \[header]\[path\_len]\[path(4B)]\[ch\_hash(3B)]\[enc(26B)]\[mac(6B)]
Plaintext: \[timestamp(4B LE)]\[0x00]\[text\\x00...]
```

### Key derivation

```python
import hashlib

def derive\_key(channel\_name: str) -> bytes:
    """
    Derive the 16-byte AES-128 key from the channel name.
    Key = first 16 bytes of SHA-256(channel\_name encoded as UTF-8).
    """
    digest = hashlib.sha256(channel\_name.encode("utf-8")).digest()
    return digest\[:16]
```

### Channel hash verification

Before decrypting, the 3-byte `ch\_hash` in the frame is used to confirm the correct channel is being used. This avoids wasted decrypt attempts across multiple known channels.

```python
def channel\_matches(channel\_name: str, ch\_hash\_bytes: bytes) -> bool:
    """
    Returns True if SHA-256(channel\_name)\[:3] matches the frame's ch\_hash field.
    """
    digest = hashlib.sha256(channel\_name.encode("utf-8")).digest()
    return digest\[:3] == ch\_hash\_bytes
```

### Decryption

```python
from Crypto.Cipher import AES   # pip install pycryptodome

def decrypt\_payload(enc: bytes, key: bytes) -> bytes | None:
    """
    Decrypt 26-byte AES-128 ECB ciphertext.
    AES block size is 16 bytes; only the first 16 bytes of `enc` form
    a full block. Bytes 16–25 are a partial second block — decrypt separately.
    """
    if len(enc) != 26:
        return None
    cipher = AES.new(key, AES.MODE\_ECB)
    # Decrypt first full block
    block1 = cipher.decrypt(enc\[:16])
    # Decrypt second partial block (padded to 16 bytes, keep first 10)
    block2\_padded = enc\[16:] + b'\\x00' \* (16 - len(enc\[16:]))
    block2 = cipher.decrypt(block2\_padded)\[:len(enc\[16:])]
    return block1 + block2
```

### Plaintext structure

After decryption the plaintext has the following layout:

```
Offset  Size    Field
──────────────────────────────────────
0       4 B     timestamp   — Unix timestamp, little-endian uint32
4       1 B     0x00        — separator / reserved byte
5       N B     text        — UTF-8 string, null-terminated (\\x00)
──────────────────────────────────────
```

```python
import struct
import datetime

def parse\_plaintext(plaintext: bytes) -> dict | None:
    if len(plaintext) < 5:
        return None

    timestamp\_raw = struct.unpack\_from("<I", plaintext, 0)\[0]
    separator     = plaintext\[4]

    # Extract null-terminated text
    text\_bytes = plaintext\[5:]
    null\_pos   = text\_bytes.find(b'\\x00')
    text       = text\_bytes\[:null\_pos].decode("utf-8", errors="replace") if null\_pos != -1 else text\_bytes.decode("utf-8", errors="replace")

    return {
        "timestamp": timestamp\_raw,
        "datetime":  datetime.datetime.utcfromtimestamp(timestamp\_raw).isoformat() + "Z",
        "separator": f"0x{separator:02X}",
        "text":      text,
    }
```

\---

## Full Parsing Pipeline

```python
def decode\_meshcore\_frame(
    transport\_bytes: bytes,
    known\_channels: list\[str],
) -> dict | None:
    """
    Full pipeline:
      1. Strip 0x88 transport wrapper
      2. Parse frame header
      3. Identify message type
      4. If CHAN MSG (0x15 / 0x16): verify ch\_hash, decrypt, parse plaintext
    Returns a decoded dict or None if frame is not decodable.
    """

    # Step 1 — extract raw payload
    raw = extract\_raw(transport\_bytes)
    if raw is None:
        return None

    # Step 2 — parse header fields
    frame = parse\_frame\_header(raw)

    # Step 3 — resolve message type
    frame\["msg\_type\_name"] = msg\_type\_name(frame\["msg\_type"])

    # Step 4 — decrypt channel messages only
    if frame\["msg\_type"] not in (0x15, 0x16):
        return frame   # control frame, no payload to decrypt

    ch\_hash\_bytes = bytes.fromhex(frame\["ch\_hash"])
    enc\_bytes     = bytes.fromhex(frame\["enc"])

    for channel\_name in known\_channels:
        if not channel\_matches(channel\_name, ch\_hash\_bytes):
            continue

        key       = derive\_key(channel\_name)
        plaintext = decrypt\_payload(enc\_bytes, key)
        if plaintext is None:
            continue

        parsed = parse\_plaintext(plaintext)
        if parsed is None:
            continue

        frame\["channel"]   = channel\_name
        frame\["plaintext"] = parsed
        return frame

    frame\["channel"]   = None
    frame\["plaintext"] = None
    frame\["error"]     = "No matching channel key found"
    return frame
```

### Example output

```json
{
  "msg\_type": 21,
  "msg\_type\_name": "CHAN MSG",
  "path\_len": 1,
  "path": "a1b2c3d4",
  "ch\_hash": "3f9a21",
  "enc": "...",
  "mac": "aabbccddeeff",
  "channel": "my-channel",
  "plaintext": {
    "timestamp": 1718000000,
    "datetime": "2024-06-10T08:53:20Z",
    "separator": "0x00",
    "text": "Hello from node 4!"
  }
}
```

\---

## Field Reference

|Field|Size|Encoding|Description|
|-|-|-|-|
|`msg\_type`|1 B|uint8|Message type (see registry)|
|`path\_len`|1 B|uint8|Number of relay hops in this frame's path|
|`path`|4 B|raw bytes|Tail 4 bytes of the relay path node ID sequence|
|`ch\_hash`|3 B|raw bytes|First 3 bytes of `SHA-256(channel\_name)`|
|`enc`|26 B|AES-128 ECB|Encrypted payload (see plaintext structure)|
|`mac`|6 B|raw bytes|Sender fingerprint / MAC suffix|
|`timestamp`|4 B|uint32 LE|Unix epoch seconds (inside decrypted plaintext)|
|`text`|N B|UTF-8, `\\x00` terminated|Message body (inside decrypted plaintext)|

\---

## Notes \& Edge Cases

* **Partial second AES block:** The 26-byte encrypted field is not a multiple of 16. Only the first 16 bytes form a complete AES block. The remaining 10 bytes are decrypted by padding the partial block to 16 bytes and keeping only the first 10 bytes of output.
* **Multiple ADVERT subtypes:** Types `0x10`–`0x13` all map to `"ADVERT"` and carry node advertisement data (node ID, name, capabilities). They do not carry encrypted payloads.
* **Multiple ACK subtypes:** `0x00`, `0x80`, `0x83` are all acknowledgement variants; their exact semantics differ by routing context.
* **ch\_hash collision:** A 3-byte hash prefix provides \~16 million possible values. False positives are theoretically possible but rare. A failed decrypt (garbage plaintext or failed null-terminator check) should be treated as a miss, not an error.
* **Transport byte `0x88`:** This is the only wrapper marker currently used by MeshCore for radio frames in AGAMA Point deployments. Future firmware may introduce additional markers.
* **Endianness:** The `timestamp` field inside the decrypted plaintext is **little-endian** (`<I` in Python struct format). All other multi-byte fields are treated as raw byte sequences without endian interpretation.

