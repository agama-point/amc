# Connects to a BLE device (using known MAC via scan), performs pairing if required,
# reads device info, enumerates services, reads readable characteristics,
# and enables MeshCore (NUS) communication (notify + send + sniff).

import asyncio
from bleak import BleakScanner, BleakClient
from amc import DEVICE_ADDRESS, NAME_CHAR, RX_CHAR

ver = "0.2/2026-03"

def notification_handler(sender, data):
    try:
        decoded = data.decode("utf-8", errors="ignore").strip()
    except Exception:
        decoded = ""
    print(f"[NOTIFY] {sender} | hex: {data.hex()} | text: {decoded}")


async def find_device_by_mac(address):
    print("=== Scanning for device ===")
    devices = await BleakScanner.discover(timeout=5.0)

    for d in devices:
        if d.address.lower() == address.lower():
            print(f"[FOUND] {d.name} | {d.address}")
            return d

    return None


async def main():
    print("amc_connect: ", ver)
    print("=== Target device ===")
    print(f"MAC: {DEVICE_ADDRESS}\n")

    # --- Scan first (required on Windows) ---
    device = await find_device_by_mac(DEVICE_ADDRESS)

    if not device:
        print("[ERR] Device not found during scan")
        return

    print("\n=== Connecting & Pairing ===")

    client = BleakClient(device, pair=True)

    await client.connect()

    # --- Pairing (important for notify/write) ---
    try:
        paired = await client.pair()
        print(f"[OK] Paired: {paired}")
    except Exception:
        print("[WARN] Pairing skipped / already paired")

    print(f"[OK] Connected: {client.is_connected}\n")

    # --- Read device name ---
    try:
        raw_name = await client.read_gatt_char(NAME_CHAR)
        device_name = raw_name.decode("utf-8").strip()
    except Exception:
        device_name = "Unknown device"

    print(f"Device name: {device_name}\n")

    # --- Load services ---
    print("=== Loading services ===")
    await asyncio.sleep(1)  # important on Windows
    services = client.services

    for service in services:
        print(f"\n[SERVICE] {service.uuid}")
        for char in service.characteristics:
            props = ",".join(char.properties)
            print(f"  [CHAR] {char.uuid} ({props})")

    # --- Read all readable characteristics ---
    print("\n=== Reading readable characteristics ===")
    for service in services:
        for char in service.characteristics:
            if "read" in char.properties:
                try:
                    value = await client.read_gatt_char(char.uuid)
                    try:
                        decoded = value.decode("utf-8").strip()
                    except Exception:
                        decoded = ""
                    print(f"{char.uuid} = {value.hex()} | text: {decoded}")
                except Exception:
                    print(f"{char.uuid} = <read error>")

    # --- Enable notifications ---
    print("\n=== Starting notification listener ===")
    try:
        await client.start_notify(RX_CHAR, notification_handler)
        print(f"[OK] Notifications enabled on {RX_CHAR}")
    except Exception as e:
        print(f"[ERR] Cannot start notify: {e}")
        await client.disconnect()
        return

    # --- Send test commands ---
    print("\n=== Sending test commands ===")
    commands = [b"info\n", b"version\n"]

    for cmd in commands:
        try:
            print(f"[SEND] {cmd}")
            await client.write_gatt_char(RX_CHAR, cmd)
            await asyncio.sleep(1)
        except Exception as e:
            print(f"[ERR] Send failed: {e}")

    # --- Sniff ---
    print("\n=== Sniffing (10 seconds) ===")
    await asyncio.sleep(10)

    # --- Cleanup ---
    await client.stop_notify(RX_CHAR)
    await client.disconnect()

    print("\n[OK] Disconnected")


asyncio.run(main())

"""
amc_connect:  0.2/2026-03
=== Target device ===
MAC: CE:2E:9F:5E:12:xx

=== Scanning for device ===
[FOUND] MeshCore-Yend@03 | CE:2E:9F:5E:12:xx

=== Connecting & Pairing ===
[OK] Paired: None
[OK] Connected: True

Device name: MeshCore-Yend@03

=== Loading services ===

[SERVICE] 00001800-0000-1000-8000-00805f9b34fb
  [CHAR] 00002a00-0000-1000-8000-00805f9b34fb (write,read)
  [CHAR] 00002a01-0000-1000-8000-00805f9b34fb (read)
  [CHAR] 00002a04-0000-1000-8000-00805f9b34fb (read)
  [CHAR] 00002aa6-0000-1000-8000-00805f9b34fb (read)

[SERVICE] 00001801-0000-1000-8000-00805f9b34fb
  [CHAR] 00002a05-0000-1000-8000-00805f9b34fb (indicate)

[SERVICE] 6e400001-b5a3-f393-e0a9-e50e24dcca9e
  [CHAR] 6e400003-b5a3-f393-e0a9-e50e24dcca9e (notify)
  [CHAR] 6e400002-b5a3-f393-e0a9-e50e24dcca9e (write,write-without-response)

=== Reading readable characteristics ===
00002a00-0000-1000-8000-00805f9b34fb = 4d657368436f72652d59656e64403033 | text: MeshCore-Yend@03
00002a01-0000-1000-8000-00805f9b34fb = 0000 | text: 
00002a04-0000-1000-8000-00805f9b34fb = 0c0018000400c800 | text: 
00002aa6-0000-1000-8000-00805f9b34fb = 01 | text: 

=== Starting notification listener ===
[OK] Notifications enabled on 6e400003-b5a3-f393-e0a9-e50e24dcca9e

=== Sending test commands ===
[SEND] b'info\n'
[SEND] b'version\n'

=== Sniffing (10 seconds) ===

=== Starting notification listener ===
[ERR] Cannot start notify: (5, 'GATT Protocol Error: Insufficient Authentication')

"""