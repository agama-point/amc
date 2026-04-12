import sys
import asyncio
import threading
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QCheckBox, QLineEdit, QLabel, QTextEdit, QFrame
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QFont

from bleak import BleakScanner, BleakClient

from amc import DEVICE_ADDRESS, NAME_CHAR, RX_CHAR, TX_CHAR

# ── BLE worker (runs in a background thread with its own event loop) ──────────
class BleWorker(QObject):
    log_signal        = pyqtSignal(str)          # append text to log
    status_signal     = pyqtSignal(str)          # update status label
    device_name_signal = pyqtSignal(str)         # update device-name label
    connected_signal  = pyqtSignal(bool)         # toggle button state

    def __init__(self):
        super().__init__()
        self._client: BleakClient | None = None
        self._loop:   asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None

    # ── public API (called from GUI thread) ──────────────────────────────────
    def connect(self, address: str):
        self._thread = threading.Thread(
            target=self._run_loop,
            args=(address,),
            daemon=True,
        )
        self._thread.start()

    def disconnect(self):
        if self._loop and self._client:
            asyncio.run_coroutine_threadsafe(self._do_disconnect(), self._loop)

    # ── internals ────────────────────────────────────────────────────────────
    def _run_loop(self, address: str):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._do_connect(address))
        finally:
            self._loop.close()
            self._loop = None

    async def _do_connect(self, address: str):
        self.log("Scanning for device …")
        self.status_signal.emit("Scanning …")

        device = None
        try:
            found = await BleakScanner.discover(timeout=5.0)
            for d in found:
                if d.address.lower() == address.lower():
                    device = d
                    break
        except Exception as e:
            self.log(f"[ERR] Scan failed: {e}")
            self.status_signal.emit("Scan error")
            self.connected_signal.emit(False)
            return

        if not device:
            self.log(f"[ERR] Device {address} not found")
            self.status_signal.emit("Not found")
            self.connected_signal.emit(False)
            return

        self.log(f"[FOUND] {device.name} | {device.address}")
        self.status_signal.emit("Connecting …")

        self._client = BleakClient(device, pair=True,
                                   disconnected_callback=self._on_disconnected)
        try:
            await self._client.connect()
        except Exception as e:
            self.log(f"[ERR] Connect failed: {e}")
            self.status_signal.emit("Connect error")
            self.connected_signal.emit(False)
            self._client = None
            return

        # pairing
        try:
            await self._client.pair()
            self.log("[OK] Paired")
        except Exception:
            self.log("[WARN] Pairing skipped / already paired")

        # device name
        try:
            raw = await self._client.read_gatt_char(NAME_CHAR)
            name = raw.decode("utf-8").strip()
        except Exception:
            name = device.name or address

        self.device_name_signal.emit(name)
        self.log(f"[OK] Connected — {name}")
        self.status_signal.emit("Connected")
        self.connected_signal.emit(True)

        # enable notifications
        try:
            await self._client.start_notify(TX_CHAR, self._on_notify)
            self.log(f"[OK] Notifications enabled on {TX_CHAR}")
        except Exception as e:
            self.log(f"[WARN] Notifications not available: {e}")

        # keep the loop alive while connected
        while self._client and self._client.is_connected:
            await asyncio.sleep(0.5)

    async def _do_disconnect(self):
        if self._client:
            try:
                await self._client.stop_notify(TX_CHAR)
            except Exception:
                pass
            try:
                await self._client.disconnect()
            except Exception:
                pass
            self._client = None

    def _on_disconnected(self, _client):
        self.log("[INFO] Device disconnected")
        self.status_signal.emit("Disconnected")
        self.device_name_signal.emit("—")
        self.connected_signal.emit(False)
        self._client = None

    def _on_notify(self, _sender, data: bytearray):
        try:
            text = data.decode("utf-8", errors="ignore").strip()
        except Exception:
            text = ""
        self.log(f"[NOTIFY] hex:{data.hex()}  text:{text}")

    def log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_signal.emit(f"{ts}  {msg}")


# ── Main window ──────────────────────────────────────────────────────────────
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AMC | MeshCore BLE")
        self.resize(640, 560)

        self._worker = BleWorker()
        self._worker.log_signal.connect(self._append_log)
        self._worker.status_signal.connect(self._set_status)
        self._worker.device_name_signal.connect(self._set_device_name)
        self._worker.connected_signal.connect(self._on_connection_changed)

        self._build_ui()
        self.apply_dark_theme()

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(12, 12, 12, 12)

        # ── top bar: MAC + connect button ─────────────────────────────────
        top = QHBoxLayout()
        self.mac_input = QLineEdit(DEVICE_ADDRESS)
        self.mac_input.setPlaceholderText("MAC address  e.g. CE:2E:9F:5E:12:AB")
        self.mac_input.setFont(QFont("Monospace", 10))

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setFixedWidth(110)
        self.connect_btn.clicked.connect(self._toggle_connection)

        top.addWidget(QLabel("Device:"))
        top.addWidget(self.mac_input, stretch=1)
        top.addWidget(self.connect_btn)
        root.addLayout(top)

        # ── info row: status pill + device name ───────────────────────────
        info = QHBoxLayout()

        self.status_label = QLabel("●  Idle")
        self.status_label.setFixedWidth(160)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)

        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Name:"))
        self.name_label = QLabel("—")
        self.name_label.setFont(QFont("Monospace", 10))
        name_row.addWidget(self.name_label)
        name_row.addStretch()

        info.addWidget(self.status_label)
        info.addWidget(sep)
        info.addLayout(name_row, stretch=1)
        root.addLayout(info)

        # ── log area ──────────────────────────────────────────────────────
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setFont(QFont("Monospace", 9))
        self.log_box.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        root.addWidget(self.log_box, stretch=1)

        # ── bottom bar: clear + dark/light toggle ─────────────────────────
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

    # ── slots ─────────────────────────────────────────────────────────────────
    @pyqtSlot(str)
    def _append_log(self, msg: str):
        self.log_box.append(msg)
        self.log_box.verticalScrollBar().setValue(
            self.log_box.verticalScrollBar().maximum()
        )

    @pyqtSlot(str)
    def _set_status(self, text: str):
        icons = {
            "Connected":    ("●", "#4caf50"),
            "Disconnected": ("●", "#f44336"),
            "Not found":    ("●", "#f44336"),
            "Scan error":   ("●", "#f44336"),
            "Connect error":("●", "#f44336"),
            "Scanning …":   ("◌", "#ffb300"),
            "Connecting …": ("◌", "#ffb300"),
        }
        icon, color = icons.get(text, ("●", "#9e9e9e"))
        self.status_label.setText(f"{icon}  {text}")
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")

    @pyqtSlot(str)
    def _set_device_name(self, name: str):
        self.name_label.setText(name)

    @pyqtSlot(bool)
    def _on_connection_changed(self, connected: bool):
        self.connect_btn.setText("Disconnect" if connected else "Connect")
        self.mac_input.setEnabled(not connected)

    def _toggle_connection(self):
        if self.connect_btn.text() == "Connect":
            addr = self.mac_input.text().strip()
            if not addr:
                self._append_log("⚠  Enter a MAC address first")
                return
            self._worker.connect(addr)
        else:
            self._worker.disconnect()

    # ── themes ────────────────────────────────────────────────────────────────
    def _toggle_theme(self):
        if self.theme_toggle.isChecked():
            self.apply_dark_theme()
        else:
            self.apply_light_theme()

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QWidget          { background:#2b2b2b; color:#e0e0e0; }
            QTextEdit,
            QLineEdit        { background:#1e1e1e; color:#e0e0e0;
                               border:1px solid #555; border-radius:4px; padding:3px; }
            QPushButton      { background:#444; color:#e0e0e0;
                               border:1px solid #666; border-radius:4px; padding:5px 10px; }
            QPushButton:hover{ background:#555; }
            QCheckBox        { color:#e0e0e0; }
            QFrame[frameShape="5"] { color:#555; }   /* VLine */
        """)

    def apply_light_theme(self):
        self.setStyleSheet("""
            QPushButton      { border:1px solid #bbb; border-radius:4px; padding:5px 10px; }
            QPushButton:hover{ background:#e0e0e0; }
            QTextEdit,
            QLineEdit        { border:1px solid #bbb; border-radius:4px; padding:3px; }
        """)


# ── entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())