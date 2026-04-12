# amc/device.py
import asyncio
from bleak import BleakClient

class Device:
    def __init__(self, address, name_char, rx_char, tx_char=None):
        """
        address   : BLE MAC address
        name_char : UUID for reading the device name
        rx_char   : UUID for writing commands (App → Firmware)  6e400002
        tx_char   : UUID for notifications   (Firmware → App)   6e400003
                    If not provided, rx_char is used (backward compatibility)
        """
        self.address   = address
        self.name_char = name_char
        self.rx_char   = rx_char
        self.tx_char   = tx_char if tx_char is not None else rx_char
        self.client    = BleakClient(address, timeout=20.0)
        self._name     = "Unknown Device"
        self.ver       = "0.2"

    async def connect(self):
        """Connects to the device and reads its name."""
        await self.client.connect()
        try:
            raw_name   = await self.client.read_gatt_char(self.name_char)
            self._name = raw_name.decode("utf-8").strip()
        except Exception:
            self._name = "MeshCore-Node"
        return True

    async def start_monitoring(self, callback):
        """Starts receiving notifications on TX char (6e400003)."""
        await self.client.start_notify(self.tx_char, callback)

    async def disconnect(self):
        """Terminates the BLE connection."""
        if self.client.is_connected:
            await self.client.disconnect()

    @property
    def name(self):
        return self._name