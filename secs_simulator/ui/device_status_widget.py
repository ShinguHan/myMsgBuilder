from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt

class DeviceStatusWidget(QFrame):
    """개별 장비의 상태를 시각적으로 표시하는 재사용 가능한 위젯입니다."""

    def __init__(self, device_id: str, host: str, port: int, parent: QWidget | None = None):
        super().__init__(parent)
        self.device_id = device_id
        
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setObjectName("statusCard")
        # 간단한 스타일링 추가
        self.setStyleSheet("""
            #statusCard {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 10px;
            }
        """)

        layout = QVBoxLayout(self)
        
        title_label = QLabel(f"<b>{device_id}</b>")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        info_layout = QHBoxLayout()
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(16, 16)
        
        self.status_label = QLabel("Stopped")
        self.status_label.setWordWrap(True)

        info_layout.addWidget(self.status_indicator)
        info_layout.addWidget(self.status_label, 1)
        layout.addLayout(info_layout)
        
        address_label = QLabel(f"{host}:{port}")
        address_label.setStyleSheet("color: #6c757d; font-size: 9pt;")
        layout.addWidget(address_label)
        
        self.update_status("Stopped", "gray")

    def update_status(self, status: str, color: str):
        """위젯의 텍스트와 상태 표시등 색상을 업데이트합니다."""
        self.status_label.setText(status)
        self.status_indicator.setStyleSheet(
            f"background-color: {color}; border-radius: 8px; border: 1px solid #adb5bd;"
        )
