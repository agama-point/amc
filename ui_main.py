# ui_main.py
# UI layer – import into amc_app.py

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QCheckBox, QLineEdit, QLabel,
    QTextBrowser, QGroupBox, QComboBox,
)
from PyQt6.QtCore import Qt, QUrl, pyqtSlot
from PyQt6.QtGui import QFont

try:
    from amc import DEVICE_ADDRESS
except ImportError:
    DEVICE_ADDRESS = ""

CHANNELS = ["#test", "#2byte", "#freebeer", "#tech", "#praha"]


class MainWindow(QWidget):
    def __init__(self, worker):
        super().__init__()
        self._worker = worker
        self.setWindowTitle("AMC | MeshCore BLE")
        self.resize(900, 640)
        self.setMinimumWidth(700)

        self._worker.log_signal.connect(self._append_log)
        self._worker.status_signal.connect(self._set_status)
        self._worker.device_name_signal.connect(self._set_device_name)
        self._worker.connected_signal.connect(self._on_connection_changed)

        self._build_ui()
        self.apply_dark_theme()

    # ------------------------------------------------------------------ #
    #  Layout                                                              #
    # ------------------------------------------------------------------ #
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(6)

        left_panel = self._build_left_panel()
        left_panel.setFixedWidth(350)
        right_panel = self._build_right_panel()

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        root.addWidget(splitter, stretch=1)

        # Bottom bar
        bottom = QHBoxLayout()
        clear_btn = QPushButton("Clear log")
        clear_btn.clicked.connect(self.log_box.clear)
        clear_btn.setFixedWidth(100)

        self.theme_toggle = QCheckBox("Dark mode")
        self.theme_toggle.setChecked(True)
        self.theme_toggle.stateChanged.connect(self._toggle_theme)

        bottom.addWidget(clear_btn)
        bottom.addStretch()
        bottom.addWidget(self.theme_toggle)
        root.addLayout(bottom)

    # ------------------------------------------------------------------ #
    #  Left panel                                                          #
    # ------------------------------------------------------------------ #
    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 4, 0)
        layout.setSpacing(10)

        layout.addWidget(self._group_ble())
        layout.addWidget(self._group_connection())
        layout.addWidget(self._group_monitoring())
        layout.addWidget(self._group_send())
        layout.addStretch()
        layout.addWidget(self._group_debug())

        return panel

    def _group_ble(self) -> QGroupBox:
        """BLE – device scan"""
        grp = QGroupBox("BLE")
        lay = QVBoxLayout(grp)
        lay.setSpacing(6)

        row = QHBoxLayout()
        self.scan_btn = QPushButton("⟳  Scan")
        self.scan_btn.clicked.connect(self._worker.scan)

        self.status_label = QLabel("● Idle")
        self.status_label.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        row.addWidget(self.scan_btn)
        row.addStretch()
        row.addWidget(self.status_label)
        lay.addLayout(row)

        return grp

    def _group_connection(self) -> QGroupBox:
        """Connection – MAC address, device name, connect/disconnect"""
        grp = QGroupBox("Connection")
        lay = QVBoxLayout(grp)
        lay.setSpacing(6)

        mac_row = QHBoxLayout()
        mac_lbl = QLabel("MAC:")
        mac_lbl.setFixedWidth(42)
        self.mac_input = QLineEdit(DEVICE_ADDRESS)
        self.mac_input.setPlaceholderText("AA:BB:CC:DD:EE:FF")
        self.mac_input.setFont(QFont("Monospace", 9))
        mac_row.addWidget(mac_lbl)
        mac_row.addWidget(self.mac_input)
        lay.addLayout(mac_row)

        name_row = QHBoxLayout()
        name_lbl = QLabel("Name:")
        name_lbl.setFixedWidth(42)
        self.name_label = QLabel("—")
        self.name_label.setFont(QFont("Monospace", 9))
        name_row.addWidget(name_lbl)
        name_row.addWidget(self.name_label, stretch=1)
        lay.addLayout(name_row)

        self.read_checkbox = QCheckBox("Enable RX notifications")
        self.read_checkbox.setChecked(True)
        self.read_checkbox.setToolTip("Subscribe to RX characteristic notifications on connect")
        lay.addWidget(self.read_checkbox)

        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self._toggle_connection)
        lay.addWidget(self.connect_btn)

        return grp

    def _group_monitoring(self) -> QGroupBox:
        """Monitoring – placeholder for future features"""
        grp = QGroupBox("Monitoring")
        lay = QVBoxLayout(grp)

        placeholder = QLabel("— not yet implemented —")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet("color: #666; font-style: italic;")
        lay.addWidget(placeholder)

        return grp

    def _group_send(self) -> QGroupBox:
        """Send – channel selector, message input, send button"""
        grp = QGroupBox("Send")
        lay = QVBoxLayout(grp)
        lay.setSpacing(6)

        # Channel selector
        ch_row = QHBoxLayout()
        ch_lbl = QLabel("Channel:")
        ch_lbl.setFixedWidth(58)
        self.channel_combo = QComboBox()
        self.channel_combo.addItems(CHANNELS)
        self.channel_combo.setFont(QFont("Monospace", 9))
        self.channel_combo.setEnabled(False)
        ch_row.addWidget(ch_lbl)
        ch_row.addWidget(self.channel_combo, stretch=1)
        lay.addLayout(ch_row)

        # Message input – Enter triggers send
        msg_row = QHBoxLayout()
        msg_lbl = QLabel("Message:")
        msg_lbl.setFixedWidth(58)
        self.msg_input = QLineEdit()
        self.msg_input.setPlaceholderText("Type your message…")
        self.msg_input.setFont(QFont("Monospace", 9))
        self.msg_input.setEnabled(False)
        self.msg_input.returnPressed.connect(self._send_message)
        msg_row.addWidget(msg_lbl)
        msg_row.addWidget(self.msg_input, stretch=1)
        lay.addLayout(msg_row)

        # Send button – enabled only when connected
        self.send_btn = QPushButton("Send  ➤")
        self.send_btn.setEnabled(False)
        self.send_btn.clicked.connect(self._send_message)
        lay.addWidget(self.send_btn)

        return grp

    def _group_debug(self) -> QGroupBox:
        """Debug toggle"""
        grp = QGroupBox("Debug")
        lay = QVBoxLayout(grp)

        self.debug_checkbox = QCheckBox("Verbose DEBUG output")
        self.debug_checkbox.setChecked(False)
        self.debug_checkbox.setToolTip("Show detailed BLE diagnostics in the log")
        lay.addWidget(self.debug_checkbox)

        return grp

    # ------------------------------------------------------------------ #
    #  Right panel – log                                                   #
    # ------------------------------------------------------------------ #
    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 0, 0, 0)
        layout.setSpacing(4)

        log_label = QLabel("Log")
        log_label.setFont(QFont("Monospace", 8))
        log_label.setStyleSheet("color: #888;")
        layout.addWidget(log_label)

        self.log_box = QTextBrowser()
        self.log_box.setReadOnly(True)
        self.log_box.setFont(QFont("Monospace", 9))
        self.log_box.setOpenExternalLinks(False)
        self.log_box.anchorClicked.connect(self._on_addr_clicked)
        layout.addWidget(self.log_box, stretch=1)

        return panel

    # ------------------------------------------------------------------ #
    #  Slots / handlers                                                    #
    # ------------------------------------------------------------------ #
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
        self.read_checkbox.setEnabled(not connected)
        # Send section unlocks only when connected
        self.send_btn.setEnabled(connected)
        self.msg_input.setEnabled(connected)
        self.channel_combo.setEnabled(connected)

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

    def _send_message(self):
        channel = self.channel_combo.currentText()
        text    = self.msg_input.text().strip()
        if not text:
            return
        self._worker.send(channel, text)
        self.msg_input.clear()

    @pyqtSlot(str)
    def _set_status(self, text: str):
        colors = {
            "Connected":    "#4caf50",
            "Scanning …":   "#ffb300",
            "Connecting …": "#ffb300",
            "Idle":         "#9e9e9e",
        }
        color = colors.get(text, "#f44336")
        self.status_label.setText(f"● {text}")
        self.status_label.setStyleSheet(f"color: {color}; font-weight: bold;")

    @pyqtSlot(str)
    def _set_device_name(self, name: str):
        self.name_label.setText(name)

    # ------------------------------------------------------------------ #
    #  Themes                                                              #
    # ------------------------------------------------------------------ #
    def _toggle_theme(self):
        if self.theme_toggle.isChecked():
            self.apply_dark_theme()
        else:
            self.apply_light_theme()

    def apply_dark_theme(self):
        self.setStyleSheet("""
            QWidget { background: #2b2b2b; color: #e0e0e0; }
            QGroupBox {
                border: 1px solid #444;
                border-radius: 6px;
                margin-top: 6px;
                padding-top: 4px;
                font-weight: bold;
                color: #aaa;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
            QTextBrowser, QLineEdit {
                background: #1e1e1e;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px;
            }
            QComboBox {
                background: #1e1e1e;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 3px 6px;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background: #1e1e1e;
                selection-background-color: #3c3c3c;
            }
            QPushButton {
                background: #3c3c3c;
                border: 1px solid #555;
                padding: 6px 10px;
                border-radius: 4px;
            }
            QPushButton:hover    { background: #505050; }
            QPushButton:pressed  { background: #2a2a2a; }
            QPushButton:disabled { color: #555; background: #2e2e2e; border-color: #3a3a3a; }
            QLineEdit:disabled   { color: #555; }
            QComboBox:disabled   { color: #555; }
            QCheckBox { spacing: 5px; }
            QSplitter::handle { background: #444; }
        """)

    def apply_light_theme(self):
        self.setStyleSheet("""
            QWidget { background: #f0f0f0; color: #222; }
            QGroupBox {
                border: 1px solid #ccc;
                border-radius: 6px;
                margin-top: 6px;
                padding-top: 4px;
                font-weight: bold;
                color: #555;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
            QTextBrowser, QLineEdit {
                background: white;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 4px;
            }
            QComboBox {
                background: white;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 3px 6px;
            }
            QPushButton {
                background: #e1e1e1;
                border: 1px solid #bbb;
                padding: 6px 10px;
                border-radius: 4px;
            }
            QPushButton:hover    { background: #d0d0d0; }
            QPushButton:disabled { color: #aaa; }
            QSplitter::handle { background: #ccc; }
        """)
