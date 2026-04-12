import sys
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout,
    QPushButton, QCheckBox, QLineEdit, QLabel, QTextEdit
)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("AMC | test app")
        self.resize(600, 500)

        layout = QVBoxLayout()

        self.label = QLabel("Status: ready")
        self.input = QLineEdit()
        self.checkbox = QCheckBox("Enable")
        self.button = QPushButton("Send")

        # přepínač dark/light
        self.theme_toggle = QCheckBox("Dark mode")
        self.theme_toggle.setChecked(True)
        self.theme_toggle.stateChanged.connect(self.toggle_theme)

        # textový blok
        self.textbox = QTextEdit()
        self.textbox.setReadOnly(True)
        self.textbox.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

        # (50 chars × 20)
        self.textbox.setFixedHeight(300)

        #  1–20
        numbers = "\n".join(str(i) for i in range(1, 21))
        self.textbox.setPlainText(numbers)

        self.button.clicked.connect(self.on_click)

        layout.addWidget(self.label)
        layout.addWidget(self.input)
        layout.addWidget(self.checkbox)
        layout.addWidget(self.button)
        layout.addWidget(self.theme_toggle)
        layout.addWidget(self.textbox)

        self.setLayout(layout)

        # default dark theme
        self.apply_dark_theme()

    def on_click(self):
        text = self.input.text()
        checked = self.checkbox.isChecked()
        self.label.setText(f"Text: {text}, Checked: {checked}")

    def toggle_theme(self):
        if self.theme_toggle.isChecked():
            self.apply_dark_theme()
        else:
            self.apply_light_theme()

    def apply_dark_theme(self):
        self.setStyleSheet("""
        QWidget {
            background-color: #2b2b2b;
            color: #ffffff;
        }
        QTextEdit, QLineEdit {
            background-color: #3b3b3b;
            color: #ffffff;
        }
        QPushButton {
            background-color: #444;
            padding: 6px;
        }
        """)

    def apply_light_theme(self):
        self.setStyleSheet("")

app = QApplication(sys.argv)
window = MainWindow()
window.show()
app.exec()