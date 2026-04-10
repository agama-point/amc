# Connects to a BLE device, reads its name, and lists all available services and characteristics.

import asyncio
from bleak import BleakClient
from amc_config import DEVICE_ADDRESS, NAME_CHAR

def notification_handler(sender, data):
    print(f"[NOTIFY] from {sender}: {data.hex()} | raw: {data}")

async def main():
    print("=== Connecting to device ===")
    print(f"Address: {DEVICE_ADDRESS}\n")

    async with BleakClient(DEVICE_ADDRESS) as client:
        print(f"[OK] Connected: {client.is_connected}\n")

        # --- Read device name ---
        try:
            raw_name = await client.read_gatt_char(NAME_CHAR)
            device_name = raw_name.decode("utf-8").strip()
        except Exception:
            device_name = "Unknown device"

        print(f"Device name: {device_name}\n")

        print("=== Loading services ===")

        await asyncio.sleep(1)  # important on Windows
        services = client.services

        for service in services:
            print(f"\n[SERVICE] {service.uuid}")

            for char in service.characteristics:
                props = ",".join(char.properties)
                print(f"  [CHAR] {char.uuid} ({props})")

asyncio.run(main())



"""
=== Connecting to device ===
Address: CE:2E:9F:5E:12:FB

[OK] Connected: True

Device name: MeshCore-Yend@03

=== Loading services ===

[SERVICE] 00001800-0000-1000-8000-00805f9b34fb
  [CHAR] 00002a00-0000-1000-8000-00805f9b34fb (read,write)
  [CHAR] 00002a01-0000-1000-8000-00805f9b34fb (read)
  [CHAR] 00002a04-0000-1000-8000-00805f9b34fb (read)
  [CHAR] 00002aa6-0000-1000-8000-00805f9b34fb (read)

[SERVICE] 00001801-0000-1000-8000-00805f9b34fb
  [CHAR] 00002a05-0000-1000-8000-00805f9b34fb (indicate)

[SERVICE] 6e400001-b5a3-f393-e0a9-e50e24dcca9e
  [CHAR] 6e400003-b5a3-f393-e0a9-e50e24dcca9e (notify)
  [CHAR] 6e400002-b5a3-f393-e0a9-e50e24dcca9e (write-without-response,write)

"""