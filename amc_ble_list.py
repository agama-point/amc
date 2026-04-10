# Agama MeshCore - BLE_list
# Scans nearby Bluetooth Low Energy (BLE) devices and prints their address, name, and RSSI in a compact one-line format.

import asyncio
from bleak import BleakScanner

async def scan():
    devices = await BleakScanner.discover(timeout=5.0)
    
    for d in devices:
        rssi = getattr(d, "rssi", None)
        rssi_str = f"{rssi} dBm" if rssi is not None else "N/A"
        print(f"{d.address} | {d.name} | {rssi_str}")

asyncio.run(scan())

"""
D8:D6:68:74:xx:xx | TY | N/A
D0:C2:4E:9A:xx:xx | [AV] Soundbar | N/A
CE:2E:9F:5E:12:FB | MeshCore-Yend@03 | N/A
44:27:F3:xx:xx:xx | XiaomiWatchS1Active 869A | N/A
A4:C1:38:67:xx:xx | 12V110Ah_010 | N/A
57:04:9D:FC:xx:xx | HLK-LD2410_F998 | N/A
C6:04:19:D0:3F:CA | MeshCore-06F53292 | N/A
C8:CA:52:9E:xx:xx | JBL Tune 520BT-LE | N/A
69:D0:50:7F:xx:xx | JBL Tune 520BT-LE | N/A
...
"""
