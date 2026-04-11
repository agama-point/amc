# amc/device.py

import asyncio
from bleak import BleakClient

class Device:
    def __init__(self, address, name_char, rx_char):
        self.address = address
        self.name_char = name_char
        self.rx_char = rx_char
        self.client = BleakClient(address, timeout=20.0)
        self._name = "Unknown Device"
        self.ver = "0.1"

    async def connect(self):
        """Connects to the device and retrieves its name."""
        await self.client.connect()
        try:
            raw_name = await self.client.read_gatt_char(self.name_char)
            self._name = raw_name.decode("utf-8").strip()
        except Exception:
            self._name = "MeshCore-Node"
        return True

    async def start_monitoring(self, callback):
        """Starts receiving notifications."""
        await self.client.start_notify(self.rx_char, callback)

    async def disconnect(self):
        """Closes the connection."""
        if self.client.is_connected:
            await self.client.disconnect()

    @property
    def name(self):
        return self._name