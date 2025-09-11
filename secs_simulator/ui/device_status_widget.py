from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt

class DeviceStatusWidget(QFrame):
    """개별 장비의 상태를 시각적으로 표시하는 재사용 가능한 위젯입니다."""

    def __init__(self, device_id: str, host: str, port: int, parent: QWidget | None = None):
        super().__init__(parent)
        self.device_id = device_id
        
        self.setObjectName("statusCard")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 8, 12, 8)
        main_layout.setSpacing(0)

        # --- 상단 (제목 & 주소) ---
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 4)
        title_label = QLabel(device_id)
        title_label.setObjectName("deviceTitle")
        
        address_label = QLabel(f"{host}:{port}")
        address_label.setObjectName("addressLabel")
        address_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        top_layout.addWidget(title_label)
        top_layout.addWidget(address_label)
        main_layout.addLayout(top_layout)

        # --- 구분선 ---
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setObjectName("cardSeparator")
        main_layout.addWidget(line)

        main_layout.addStretch(1)

        # --- 하단 (상태) ---
        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(0, 4, 0, 0)
        self.status_indicator = QLabel()
        self.status_indicator.setObjectName("statusIndicator")

        self.status_label = QLabel("Stopped")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setWordWrap(True)

        status_layout.addWidget(self.status_indicator)
        status_layout.addWidget(self.status_label, 1)
        main_layout.addLayout(status_layout)
        
        self.update_status("Stopped", "#555555")

    def update_status(self, status: str, color: str):
        """위젯의 텍스트와 상태 표시등 색상을 업데이트합니다."""
        self.status_label.setText(status)
        self.status_indicator.setStyleSheet(f"background-color: {color};")