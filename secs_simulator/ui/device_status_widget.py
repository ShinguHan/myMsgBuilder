# secs_simulator/ui/device_status_widget.py

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton
from PySide6.QtCore import Qt, Signal

class DeviceStatusWidget(QFrame):
    toggled = Signal(str, bool)

    def __init__(self, device_id: str, host: str, port: int, connection_mode: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.device_id = device_id
        self.is_active = False
        
        self.setObjectName("statusCard")

        # 모든 요소를 세로로 배치하는 메인 레이아웃입니다.
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 8, 12, 8)
        main_layout.setSpacing(5)

        # --- 상단: 제목과 주소 ---
        mode_char = "A" if connection_mode == "Active" else "P"
        title_label = QLabel(f"<b>{device_id}</b> ({mode_char})")
        title_label.setObjectName("deviceTitle")
        
        address_label = QLabel(f"{host}:{port}")
        address_label.setObjectName("addressLabel")

        # --- 중간: 상태 표시 ---
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(6)
        
        self.status_indicator = QLabel()
        self.status_indicator.setObjectName("statusIndicator")
        
        self.status_label = QLabel("Stopped")
        self.status_label.setObjectName("statusLabel")

        status_layout.addWidget(self.status_indicator)
        status_layout.addWidget(self.status_label)
        status_layout.addStretch() # 상태 텍스트가 왼쪽으로 붙도록

        # --- 하단: 제어 버튼 ---
        self.toggle_button = QPushButton("OFF")
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)
        self.toggle_button.setObjectName("deviceToggleButton")
        self.toggle_button.setFixedSize(60, 28)
        self.toggle_button.toggled.connect(self.on_toggle)
        
        # 생성된 위젯들을 메인 레이아웃에 순서대로 추가합니다.
        main_layout.addWidget(title_label)
        main_layout.addWidget(address_label)
        main_layout.addWidget(status_widget)
        main_layout.addWidget(self.toggle_button, 0, Qt.AlignmentFlag.AlignLeft) # 버튼을 좌측 정렬

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