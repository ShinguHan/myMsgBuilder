from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton
from PySide6.QtCore import Qt, Signal

class DeviceStatusWidget(QFrame):
    toggled = Signal(str, bool)

    def __init__(self, device_id: str, host: str, port: int, connection_mode: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.device_id = device_id
        self.is_active = False
        
        self.setObjectName("statusCard")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 8, 12, 8)
        
        top_layout = QHBoxLayout()
        mode_char = "A" if connection_mode == "Active" else "P"
        title_label = QLabel(f"{device_id} ({mode_char})")
        title_label.setObjectName("deviceTitle")
        
        address_label = QLabel(f"{host}:{port}")
        address_label.setObjectName("addressLabel")
        address_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.toggle_button = QPushButton("Off")
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)
        self.toggle_button.setObjectName("deviceToggleButton")
        self.toggle_button.setFixedWidth(60)
        self.toggle_button.toggled.connect(self.on_toggle)
        
        top_layout.addWidget(title_label)
        top_layout.addStretch()
        top_layout.addWidget(address_label)
        top_layout.addWidget(self.toggle_button)
        main_layout.addLayout(top_layout)

        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(0, 4, 0, 0)
        self.status_indicator = QLabel()
        self.status_indicator.setObjectName("statusIndicator")

        self.status_label = QLabel("Stopped")
        self.status_label.setObjectName("statusLabel")

        status_layout.addWidget(self.status_indicator)
        status_layout.addWidget(self.status_label, 1)
        main_layout.addLayout(status_layout)
        
        self.update_status("Stopped", "gray", False)

    def on_toggle(self, checked: bool):
        self.is_active = checked
        if checked:
            self.toggle_button.setText("ON")
            self.toggle_button.setStyleSheet("background-color: #34C759;") # Green
        else:
            self.toggle_button.setText("OFF")
            self.toggle_button.setStyleSheet("background-color: #555555;") # Default gray
        self.toggled.emit(self.device_id, checked)

    def update_status(self, status: str, color: str, is_active: bool):
        self.status_label.setText(status)
        self.status_indicator.setStyleSheet(f"background-color: {color};")
        
        was_active = self.is_active
        self.is_active = is_active
        if was_active != self.is_active:
            self.toggle_button.setChecked(is_active)

