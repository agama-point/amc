# amc/send.py
"""
MeshCore BLE channel message sender.
P ímý Companion Radio Protocol.
Zdroj: https://docs.meshcore.io/companion_protocol/

Očekává již připojený Device objekt – připojení řídí volající skript.
"""

import asyncio
import struct
import time
from amc import TX_CHAR, RX_CHAR
from amc.device import Device

VER = "0.2/2026-04"

# ── Companion Radio Protocol opcodes ──────────────────────────
CMD_APP_START            = 0x01
CMD_SEND_CHANNEL_TXT_MSG = 0x03
CMD_GET_CHANNEL          = 0x1F

RESP_OK           = 0x00
RESP_ERROR        = 0x01
RESP_SELF_INFO    = 0x05
RESP_MSG_SENT     = 0x06
RESP_CHANNEL_INFO = 0x12

KNOWN_RESP = {
    0x00: "RESP_OK",          0x01: "RESP_ERROR",
    0x05: "RESP_SELF_INFO",   0x06: "RESP_MSG_SENT",
    0x12: "RESP_CHANNEL_INFO",
    0x83: "PUSH_MSG_WAITING", 0x80: "PUSH_ADVERT",
}

# ── Výpis ──────────────────────────────────────────────────────
def _dbg(debug: bool, msg: str):
    if debug:
        print(f"  [DBG] {msg}")

def _info(msg: str):
    print(f"  {msg}")

def _section(title: str):
    print(f"\n{'─'*55}")
    print(f"  ◆ {title}")
    print(f"{'─'*55}")

# ── Stavba paketů ──────────────────────────────────────────────
def _build_app_start() -> bytes:
    return bytes([CMD_APP_START]) + bytes(7) + b"amcsend"

def _build_get_channel(idx: int) -> bytes:
    return bytes([CMD_GET_CHANNEL, idx])

def _build_send_channel_msg(chan_idx: int, text: str) -> bytes:
    ts_bytes  = struct.pack("<I", int(time.time()))
    txt_bytes = text.encode("utf-8")
    return bytes([CMD_SEND_CHANNEL_TXT_MSG, 0x00, chan_idx]) + ts_bytes + txt_bytes

def _parse_channel_info(data: bytes) -> dict | None:
    if len(data) < 2 or data[0] != RESP_CHANNEL_INFO:
        return None
    chan_idx = data[1]
    name_raw = data[2:34] if len(data) >= 34 else data[2:]
    name     = name_raw.split(b"\x00")[0].decode("utf-8", errors="ignore").strip()
    secret   = data[34:50] if len(data) >= 50 else b""
    return {"idx": chan_idx, "name": name, "secret": secret}

# ── BLE vrstva ─────────────────────────────────────────────────
class _Sender:
    def __init__(self, dev: Device, debug: bool):
        self.dev   = dev
        self.debug = debug
        self._response: bytes | None = None
        self._event = asyncio.Event()

    def _on_notify(self, sender, data: bytearray):
        raw   = bytes(data)
        label = KNOWN_RESP.get(raw[0], f"0x{raw[0]:02X}")
        _dbg(self.debug, f"[BLE ← TX] {len(raw)}B | {label} | {raw.hex().upper()}")
        self._response = raw
        self._event.set()

    async def _write(self, cmd: bytes, wait: bool = True, timeout: float = 4.0) -> bytes | None:
        self._response = None
        self._event.clear()
        _dbg(self.debug, f"[BLE → RX] {len(cmd)}B: {cmd.hex().upper()}")
        await self.dev.client.write_gatt_char(RX_CHAR, cmd, response=True)
        _dbg(self.debug, "  write OK")
        if not wait:
            return None
        _dbg(self.debug, f"  čekám na notify (timeout={timeout}s)...")
        try:
            await asyncio.wait_for(self._event.wait(), timeout)
            _dbg(self.debug, "  notify přijat ✓")
            return self._response
        except asyncio.TimeoutError:
            _dbg(self.debug, f"  ⚠ timeout {timeout}s")
            return None

    async def app_start(self):
        _section("APP START")
        _info("Posílám CMD_APP_START [0x01]...")
        raw = await self._write(_build_app_start(), timeout=5.0)
        if raw is None:
            _info("⚠ Žádná odpověď na APP_START")
        elif raw[0] == RESP_SELF_INFO:
            _info(f"✅ RESP_SELF_INFO – firmware připraven ({len(raw)}B)")
            _dbg(self.debug, f"  raw: {raw.hex().upper()}")
        else:
            _info(f"⚠ Odpověď: 0x{raw[0]:02X} | {raw.hex().upper()}")
        await asyncio.sleep(0.3)

    async def find_channel(self, name: str) -> int | None:
        _section(f"HLEDÁM KANÁL: '{name}'")
        _info("CMD_GET_CHANNEL [0x1F][idx] pro sloty 0–7...")
        _info("")
        found = []
        for idx in range(8):
            _dbg(self.debug, f"── slot {idx} ──")
            raw = await self._write(_build_get_channel(idx), timeout=3.0)
            if raw is None:
                _info(f"  slot {idx}: (timeout)")
                continue
            ch = _parse_channel_info(raw)
            if ch is None:
                _info(f"  slot {idx}: neznámá odpověď 0x{raw[0]:02X}")
                continue
            ch_name = ch["name"]
            found.append(ch_name)
            match = ch_name.lower() == name.lower()
            _info(f"  slot {idx}: '{ch_name}'" + ("  ✅ SHODA!" if match else ""))
            if match:
                return idx
        _info("")
        if not found:
            _info("⚠ Žádný slot nevrátil RESP_CHANNEL_INFO (0x12)")
        else:
            _info(f"  Nalezené kanály: {found}")
            _info(f"  '{name}' mezi nimi není.")
        return None

    async def send_message(self, chan_idx: int, text: str) -> bool:
        _section("ODESÍLÁM ZPRÁVU")
        _info(f"Kanál  : slot {chan_idx}")
        _info(f"Zpráva : \"{text}\"")
        cmd = _build_send_channel_msg(chan_idx, text)
        _info(f"Paket  : {len(cmd)}B → {cmd.hex().upper()}")
        _info("")
        raw = await self._write(cmd, timeout=6.0)
        if raw is None:
            _info("⚠ Žádná odpověď – BLE write proběhl, zpráva pravděpodobně odeslána")
            return True
        if raw[0] in (RESP_MSG_SENT, RESP_OK):
            label = "RESP_MSG_SENT (0x06)" if raw[0] == RESP_MSG_SENT else "RESP_OK (0x00)"
            _info(f"✅ {label} – potvrzeno!")
            return True
        elif raw[0] == RESP_ERROR:
            _info("❌ RESP_ERROR (0x01)")
            return False
        else:
            _info(f"⚠ Odpověď: 0x{raw[0]:02X} – považuji za OK")
            return True


# ── Veřejné API ────────────────────────────────────────────────

async def send_channel_msg(
    dev:     Device,
    channel: str,
    message: str,
    debug:   bool = False,
) -> bool:
    """
    Odešle zprávu do MeshCore kanálu přes BLE.

    Parametry:
        dev     : již připojený Device objekt (připojení řídí volající)
        channel : název kanálu, např. "#test"
        message : text zprávy
        debug   : True = verbose/debug výstup

    Vrací:
        True  = zpráva odeslána
        False = chyba
    """
    _dbg(debug, f"amc/send.py ver {VER}")
    _dbg(debug, f"RX char (write) : {RX_CHAR}")
    _dbg(debug, f"TX char (notify): {TX_CHAR}")

    sender = _Sender(dev, debug)

    # Notifikace na TX char (6e400003)
    _section("BLE NOTIFIKACE")
    _info(f"Registruji notify na TX char: {TX_CHAR}...")
    try:
        await dev.client.start_notify(TX_CHAR, sender._on_notify)
        _info("✅ Notifikace aktivní")
    except Exception as e:
        _info(f"❌ Nelze spustit notifikace: {e}")
        return False

    await asyncio.sleep(0.2)

    try:
        # Handshake
        await sender.app_start()

        # Najdi kanál
        chan_idx = await sender.find_channel(channel)
        if chan_idx is None:
            _section("VÝSLEDEK")
            _info(f"❌ Kanál '{channel}' nebyl nalezen na zařízení.")
            return False

        _section("KANÁL NALEZEN")
        _info(f"✅ '{channel}' → slot {chan_idx}")

        # Odešli zprávu
        ok = await sender.send_message(chan_idx, message)

        _section("VÝSLEDEK")
        if ok:
            print(f"\n  ✅ Zpráva odeslána do [{channel}]: \"{message}\"")
        else:
            print(f"\n  ❌ Odeslání selhalo.")
        return ok

    finally:
        try:
            await dev.client.stop_notify(TX_CHAR)
            _dbg(debug, "stop_notify OK")
        except Exception:
            pass