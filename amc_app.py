# amc_app.py

import sys
import asyncio
import threading
from datetime import datetime

version = "0.2 | 2026-03"

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QCheckBox, QLineEdit, QLabel, QTextEdit, QTextBrowser, QFrame
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal, pyqtSlot, QUrl
from PyQt6.QtGui import QFont

from bleak import BleakScanner, BleakClient

# - Configuration ------------------------------
try:
    from amc import DEVICE_ADDRESS, NAME_CHAR, RX_CHAR, TX_CHAR
except ImportError:
    DEVICE_ADDRESS = ""
    NAME_CHAR = "00002a00-0000-1000-8000-00805f9b34fb"
    RX_CHAR = None # Obvykle se čte z RX (z pohledu periferie TX)
    TX_CHAR = None

# - BLE worker ----------------------------
class BleWorker(QObject):
    log_signal         = pyqtSignal(str)
    status_signal      = pyqtSignal(str)
    device_name_signal = pyqtSignal(str)
    connected_signal   = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self._client: BleakClient | None = None
        self._loop:   asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._ensure_loop()

    def _ensure_loop(self):
        if self._thread is None or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()

    def _run_loop(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_forever()

    def connect(self, address: str, do_read: bool):
        asyncio.run_coroutine_threadsafe(self._do_connect(address, do_read), self._loop)

    def disconnect(self):
        if self._loop and self._client:
            asyncio.run_coroutine_threadsafe(self._do_disconnect(), self._loop)

    def scan(self):
        asyncio.run_coroutine_threadsafe(self._do_scan(), self._loop)

    async def _do_scan(self):
        self.log("<i>Scanning BLE (5s)...</i>")
        self.status_signal.emit("Scanning …")
        try:
            devices_dict = await BleakScanner.discover(timeout=5.0, return_adv=True)
            if not devices_dict:
                self.log("No devices found.")
            else:
                sorted_items = sorted(
                    devices_dict.values(),
                    key=lambda x: x[1].rssi if x[1].rssi is not None else -100,
                    reverse=True
                )
                for device, adv_data in sorted_items:
                    rssi = adv_data.rssi if adv_data.rssi is not None else "N/A"
                    name = device.name if device.name else "Unknown"
                    link = f"<a href='{device.address}' style='color: #2196f3; font-weight: bold;'>{device.address}</a>"
                    self.log(f"[SCAN] {link} | {name} | {rssi} dBm")
        except Exception as e:
            self.log(f"[ERR] Scan failed: {e}")

        is_conn = self._client.is_connected if self._client else False
        self.status_signal.emit("Connected" if is_conn else "Idle")

  
    async def _do_connect(self, address: str, do_read: bool):
        self.log(f"Connecting to {address}...")
        self.status_signal.emit("Connecting …")
        try:
            self._client = BleakClient(address, disconnected_callback=self._on_disconnected)
            await self._client.connect()

            # Načtení služeb pro diagnostiku
            services = self._client.services
            
            # Read device name
            name = address
            try:
                if NAME_CHAR:
                    raw = await self._client.read_gatt_char(NAME_CHAR)
                    name = raw.decode("utf-8").strip()
            except: pass

            self.device_name_signal.emit(name)
            self.log(f"<b style='color:#4caf50;'>[OK] Connected: {name}</b>")
            self.status_signal.emit("Connected")
            self.connected_signal.emit(True)

            # Notifications (RX)
            if do_read:
                if not RX_CHAR:
                    self.log("<span style='color:orange;'>[WARN] RX_CHAR UUID is not defined!</span>")
                else:
                    char = services.get_characteristic(RX_CHAR)
                    if char:
                        # Diagnostika: co charakteristika reálně umí?
                        props = char.properties
                        self.log(f"<small style='color:#888;'>RX Props: {', '.join(props)}</small>")
                        
                        if "notify" in props or "indicate" in props:
                            await self._client.start_notify(RX_CHAR, self._on_notify)
                            self.log(f"<i style='color:#bbb;'>Notifications enabled on {RX_CHAR}</i>")
                        else:
                            self.log(f"<span style='color:red;'>[ERR] {RX_CHAR} does not support notifications! (Props: {props})</span>")
                    else:
                        self.log(f"<span style='color:red;'>[ERR] Characteristic {RX_CHAR} not found on device!</span>")
            else:
                self.log("<i>Reading (RX) disabled by user.</i>")

        except Exception as e:
            self.log(f"[ERR] Connection failed: {e}")
            self.status_signal.emit("Connect error")
            self.connected_signal.emit(False) 
    

    async def _do_disconnect(self):
        if self._client:
            # Bleak automaticky zastaví notifikace při odpojení, 
            # ale explicitní volání je čistší pokud bychom chtěli zůstat připojeni
            await self._client.disconnect()
            self._client = None

    def _on_disconnected(self, _client):
        self.log("<b style='color:#f44336;'>[INFO] Disconnected</b>")
        self.status_signal.emit("Disconnected")
        self.device_name_signal.emit("—")
        self.connected_signal.emit(False)

    def _on_notify(self, _sender, data: bytearray):
        try:
            text = data.decode("utf-8", errors="ignore").strip()
            self.log(f"<span style='color:#bbb;'>[RX]</span> {text}")
        except:
            self.log(f"[RX HEX] {data.hex()}")

    def log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_signal.emit(f"<span style='color:#666;'>{ts}</span> &nbsp;{msg}")


# - Main window ---------------------------
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"AMC | MeshCore BLE v{version}")
        self.resize(720, 600)

        self._worker = BleWorker()
        self._worker.log_signal.connect(self._append_log)
        self._worker.status_signal.connect(self._set_status)
        self._worker.device_name_signal.connect(self._set_device_name)
        self._worker.connected_signal.connect(self._on_connection_changed)

        self._build_ui()
        self.apply_dark_theme()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(15, 15, 15, 15)
        root.setSpacing(10)

        # Top bar
        top = QHBoxLayout()
        self.mac_input = QLineEdit(DEVICE_ADDRESS)
        self.mac_input.setPlaceholderText("MAC Address (e.g. AA:BB:CC...)")
        self.mac_input.setFont(QFont("Monospace", 10))

        self.scan_btn = QPushButton("Scan")
        self.scan_btn.setFixedWidth(80)
        self.scan_btn.clicked.connect(self._worker.scan)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setFixedWidth(100)
        self.connect_btn.clicked.connect(self._toggle_connection)

        top.addWidget(QLabel("Device:"))
        top.addWidget(self.mac_input, stretch=1)
        top.addWidget(self.scan_btn)
        top.addWidget(self.connect_btn)
        root.addLayout(top)

        # Info & Options row
        info = QHBoxLayout()
        self.status_label = QLabel("● Idle")
        self.status_label.setFixedWidth(140)

        self.name_label = QLabel("—")
        self.name_label.setFont(QFont("Monospace", 10))
        
        # New: Read Checkbox
        self.read_checkbox = QCheckBox("Read (RX)")
        self.read_checkbox.setChecked(True)
        self.read_checkbox.setToolTip("Enable notifications from RX characteristic on connect")

        info.addWidget(self.status_label)
        info.addWidget(QLabel("Name:"))
        info.addWidget(self.name_label, stretch=1)
        info.addWidget(self.read_checkbox)
        root.addLayout(info)

        # Log
        self.log_box = QTextBrowser()
        self.log_box.setReadOnly(True)
        self.log_box.setFont(QFont("Monospace", 9))
        self.log_box.setOpenExternalLinks(False)
        self.log_box.anchorClicked.connect(self._on_addr_clicked)
        root.addWidget(self.log_box)

        # Bottom
        bottom = QHBoxLayout()
        clear_btn = QPushButton("Clear log")
        clear_btn.clicked.connect(self.log_box.clear)

        self.theme_toggle = QCheckBox("Dark mode")
        self.theme_toggle.setChecked(True)
        self.theme_toggle.stateChanged.connect(self._toggle_theme)

        bottom.addWidget(clear_btn)
        bottom.addStretch()
        bottom.addWidget(self.theme_toggle)
        root.addLayout(bottom)

    @pyqtSlot(str)
    def _append_log(self, html_msg: str):
        self.log_box.append(html_msg)
        self.log_box.verticalScrollBar().setValue(
            self.log_box.verticalScrollBar().maximum()
        )

    @pyqtSlot(bool)
    def _on_connection_changed(self, connected: bool):
        self.connect_btn.setText("Disconnect" if connected else "Connect")
        self.mac_input.setEnabled(not connected)
        self.scan_btn.setEnabled(not connected)
        self.read_checkbox.setEnabled(not connected) # Neměnit během spojení

    def _on_addr_clicked(self, url: QUrl):
        addr = url.toString()
        self.mac_input.setText(addr)
        self._append_log(f"<i style='color:#888;'>Selected: {addr}</i>")

    def _toggle_connection(self):
        if self.connect_btn.text() == "Connect":
            addr = self.mac_input.text().strip()
            do_read = self.read_checkbox.isChecked()
            if addr:
                self._worker.connect(addr, do_read)
        else:
            self._worker.disconnect()

    @pyqtSlot(str)
    def _set_status(self, text: str):
        colors = {
            "Connected": "#4caf50",
            "Scanning …": "#ffb300",
            "Connecting …": "#ffb300",
            "Idle": "#9e9e9e"
        }
        color = colors.get(text, "#f44336")
        self.status_label.setText(f"● {text}")
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")

    @pyqtSlot(str)
    def _set_device_name(self, name: str):
        self.name_label.setText(name)

    def _toggle_theme(self):
        if self.theme_toggle.isChecked():
            self.apply_dark_theme()
        else:
            self.apply_light_theme()

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QWidget { background:#2b2b2b; color:#e0e0e0; }
            QTextBrowser, QLineEdit {
                background:#1e1e1e;
                border:1px solid #555;
                border-radius:4px;
                padding:4px;
            }
            QPushButton {
                background:#444;
                border:1px solid #666;
                padding:6px;
                border-radius:4px;
            }
            QPushButton:hover { background:#555; }
            QCheckBox { spacing: 5px; }
        """)

    def apply_light_theme(self):
        self.setStyleSheet("""
            QWidget { background:#f5f5f5; color:#222; }
            QTextBrowser, QLineEdit {
                background:white;
                border:1px solid #ccc;
                border-radius:4px;
                padding:4px;
            }
            QPushButton {
                background:#e1e1e1;
                border:1px solid #bbb;
                padding:6px;
                border-radius:4px;
            }
        """)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())