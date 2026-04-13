# amc_app.py

import sys
import asyncio
import threading
from datetime import datetime

version = "0.3.1 | 2026-04"

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal
from bleak import BleakScanner

from ui_main import MainWindow

# - Configuration -----------------------------------------------------
try:
    from amc import DEVICE_ADDRESS, NAME_CHAR, RX_CHAR, TX_CHAR
    from amc.device import Device  # Importujeme Device třídu
except ImportError:
    DEVICE_ADDRESS = ""
    NAME_CHAR = "00002a00-0000-1000-8000-00805f9b34fb"
    RX_CHAR   = None
    TX_CHAR   = None

try:
    from amc.send import send_channel_msg
    _SEND_AVAILABLE = True
except ImportError:
    _SEND_AVAILABLE = False


# - BLE worker --------------------------------------------------------
class BleWorker(QObject):
    log_signal         = pyqtSignal(str)
    status_signal      = pyqtSignal(str)
    device_name_signal = pyqtSignal(str)
    connected_signal   = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        # Místo _client budeme používat instanci Device z vaší knihovny
        self.dev: Device | None = None
        self._loop:   asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._debug:  bool = False
        self._ensure_loop()

    # ---- Public API -------------------------------------------------
    def set_debug(self, enabled: bool):
        self._debug = enabled

    def connect(self, address: str, do_read: bool):
        asyncio.run_coroutine_threadsafe(
            self._do_connect(address, do_read), self._loop
        )

    def disconnect(self):
        if self._loop and self.dev:
            asyncio.run_coroutine_threadsafe(self._do_disconnect(), self._loop)

    def scan(self):
        asyncio.run_coroutine_threadsafe(self._do_scan(), self._loop)

    def send(self, channel: str, message: str):
        asyncio.run_coroutine_threadsafe(
            self._do_send(channel, message), self._loop
        )

    # ---- Event loop -------------------------------------------------
    def _ensure_loop(self):
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    # ---- Coroutines -------------------------------------------------
    async def _do_scan(self):
        self.log("<i>Scanning BLE (5 s)…</i>")
        self.status_signal.emit("Scanning …")
        try:
            devices_dict = await BleakScanner.discover(timeout=5.0, return_adv=True)
            if not devices_dict:
                self.log("No devices found.")
            else:
                sorted_items = sorted(
                    devices_dict.values(),
                    key=lambda x: x[1].rssi if x[1].rssi is not None else -100,
                    reverse=True,
                )
                for device, adv_data in sorted_items:
                    rssi = adv_data.rssi if adv_data.rssi is not None else "N/A"
                    name = device.name or "Unknown"
                    link = f"<a href='{device.address}' style='color:#2196f3; font-weight:bold;'>{device.address}</a>"
                    self.log(f"[SCAN] {link} &nbsp;| {name} | {rssi} dBm")
        except Exception as e:
            self.log(f"<span style='color:red;'>[ERR] Scan failed: {e}</span>")

        is_conn = self.dev.is_connected if self.dev else False
        self.status_signal.emit("Connected" if is_conn else "Idle")

    async def _do_connect(self, address: str, do_read: bool):
        self.log(f"Connecting to <b>{address}</b>…")
        self.status_signal.emit("Connecting …")
        try:
            # Inicializace Device objektu (stejně jako v amc_send.py)
            self.dev = Device(address, NAME_CHAR, RX_CHAR)
            
            # Pokud vaše třída Device interně používá callback pro odpojení, 
            # museli bychom ho nastavit zde, ale pro začátek použijeme await connect()
            await self.dev.connect()

            self.device_name_signal.emit(self.dev.name)
            self.log(f"<b style='color:#4caf50;'>[OK] Connected: {self.dev.name}</b>")
            self.status_label_update = "Connected"
            self.status_signal.emit("Connected")
            self.connected_signal.emit(True)

            # Pokud třída Device sama neřeší notifikace automaticky, 
            # a potřebujete je ovládat z GUI:
            if do_read and hasattr(self.dev, 'client') and self.dev.client:
                # Tohle je trochu "hack", pokud Device neexponuje start_notify přímo
                try:
                    await self.dev.client.start_notify(RX_CHAR, self._on_notify)
                    self.log(f"<i style='color:#bbb;'>RX notifications enabled</i>")
                except:
                    pass

        except Exception as e:
            self.log(f"<span style='color:red;'>[ERR] Connection failed: {e}</span>")
            self.status_signal.emit("Connect error")
            self.connected_signal.emit(False)

    async def _do_disconnect(self):
        if self.dev:
            await self.dev.disconnect()
            self.dev = None

    async def _do_send(self, channel: str, message: str):
        if not _SEND_AVAILABLE or not self.dev:
            self.log("<span style='color:orange;'>[WARN] Cannot send - not connected or module missing.</span>")
            return

        self.log(f"<span style='color:#bbb;'>[TX] {channel} &rarr; {message}</span>")

        try:
            # VOLÁNÍ OPRAVENO PODLE amc_send.py
            ok = await send_channel_msg(
                dev=self.dev,       # Předáváme instanci Device
                channel=channel,
                message=message,
                debug=self._debug,
            )
            
            if ok:
                self.log(f"<span style='color:#4caf50;'>[OK] Sent to {channel}</span>")
            else:
                self.log(f"<span style='color:red;'>[ERR] send_channel_msg returned False</span>")
        except Exception as e:
            self.log(f"<span style='color:red;'>[ERR] Send failed: {e}</span>")

    # ---- Callbacks & Logging ----------------------------------------
    def _on_notify(self, _sender, data: bytearray):
        # ... stejné jako předtím ...
        text = data.decode("utf-8", errors="ignore").strip()
        self.log(f"<span style='color:#bbb;'>[RX]</span> {text}")

    def log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_signal.emit(f"<span style='color:#555;'>{ts}</span> &nbsp;{msg}")

# - Entry point (stejný jako dříve) -----------------------------------
if __name__ == "__main__":
    app    = QApplication(sys.argv)
    worker = BleWorker()
    win    = MainWindow(worker)
    win.debug_checkbox.stateChanged.connect(lambda state: worker.set_debug(bool(state)))
    win.show()
    sys.exit(app.exec())