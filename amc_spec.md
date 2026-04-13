# MeshCore Protocol --- AGAMA Point Integration Specification

> **AMC \| AGAMA_POINT MESHCORE decoder** --- internal reference for how
> raw frames are extracted, parsed, and decrypted from the MeshCore
> transport layer.

------------------------------------------------------------------------

## Table of Contents

1.  [Overview](#overview)
2.  [Transport Layer --- RAW Hex
    Extraction](#transport-layer--raw-hex-extraction)
3.  [Frame Structure](#frame-structure)
4.  [Message Type Registry](#message-type-registry)
5.  [Channel Message Decryption
    (GRP_TXT)](#channel-message-decryption-grp_txt)
6.  [Full Parsing Pipeline](#full-parsing-pipeline)
7.  [Field Reference](#field-reference)
8.  [Notes & Edge Cases](#notes--edge-cases)

------------------------------------------------------------------------

## Overview

MeshCore is a LoRa-based mesh networking protocol. Nodes exchange binary
frames over a radio transport. AGAMA Point intercepts these frames at
the transport boundary, extracts raw hex payloads wrapped in the `0x88`
marker, and decodes them into structured messages --- including
decrypting AES-128 ECB group channel text.

    [Radio RX] → [Transport Layer 0x88 wrapper] → [RAW hex] → [Frame parser] → [Decryptor] → [Decoded message]

------------------------------------------------------------------------

## Transport Layer --- RAW Hex Extraction

Frames arrive wrapped in the MeshCore transport envelope. The outer
wrapper is identified by the leading byte `0x88`, which signals a
MeshCore radio frame.

### Extraction procedure

``` python
def extract_raw(transport_bytes: bytes) -> bytes | None:
    if len(transport_bytes) < 2:
        return None
    if transport_bytes[0] != 0x88:
        return None
    return transport_bytes[1:]
```

------------------------------------------------------------------------

## Frame Structure

    Offset  Size    Field
    0       1 B     msg_type
    1       1 B     path_len
    2       4 B     path
    6       3 B     ch_hash
    9       26 B    enc_payload
    35      6 B     mac
    Total:  41 B

------------------------------------------------------------------------

## Message Type Registry

``` python
_MSG_TYPES = {
    0x15: "CHAN MSG",
    0x16: "CHAN MSG",
}
```

------------------------------------------------------------------------

## Channel Message Decryption (GRP_TXT)

    Algorithm: AES-128 ECB
    Key: SHA256(channel_name)[:16]
    Plaintext: [timestamp][0x00][text\x00...]

------------------------------------------------------------------------

## Full Parsing Pipeline

``` python
def decode_meshcore_frame(transport_bytes: bytes, known_channels: list[str]):
    raw = extract_raw(transport_bytes)
    if raw is None:
        return None
```

------------------------------------------------------------------------

## Field Reference

  Field      Size   Description
  ---------- ------ --------------
  msg_type   1B     Type
  path_len   1B     Hops
  path       4B     Path
  ch_hash    3B     Channel hash
  enc        26B    Encrypted
  mac        6B     MAC

------------------------------------------------------------------------

## Notes

-   Partial AES block handling required
-   Timestamp is little-endian
