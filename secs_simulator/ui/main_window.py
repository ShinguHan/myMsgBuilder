from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QPushButton, QGridLayout, QTextEdit, QScrollArea)
from PySide6.QtCore import Signal, Slot, QObject
from typing import Dict

from secs_simulator.engine.orchestrator import Orchestrator
from secs_simulator.ui.device_status_widget import DeviceStatusWidget

class MainWindow(QMainWindow):
    """애플리케이션의 메인 윈도우 클래스."""
    
    # 백그라운드(asyncio) 스레드에서 UI를 안전하게 업데이트하기 위한 Signal
    # str, str, str -> device_id, status_message, color
    agent_status_updated = Signal(str, str, str)

    def __init__(self, orchestrator: Orchestrator):
        super().__init__()
        self.orchestrator = orchestrator
        self.device_widgets: Dict[str, DeviceStatusWidget] = {}

        self.setWindowTitle("SECS/HSMS Multi-Device Simulator")
        self.setGeometry(100, 100, 1200, 800)

        # Signal과 Slot을 연결
        self.agent_status_updated.connect(self.on_agent_status_update)

        self._init_ui()

    def _init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # --- 왼쪽: 장비 상태 패널 ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        control_layout = QHBoxLayout()
        self.start_button = QPushButton("Start All Agents")
        self.stop_button = QPushButton("Stop All Agents")
        self.stop_button.setEnabled(False)
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)
        left_layout.addLayout(control_layout)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        self.device_grid_layout = QGridLayout(scroll_content)
        scroll_area.setWidget(scroll_content)
        left_layout.addWidget(scroll_area)
        
        # --- 오른쪽: 로그 및 시나리오 패널 (현재는 로그만) ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        
        right_layout.addWidget(self.log_display)
        # TODO: 향후 여기에 시나리오 실행 버튼 및 편집기가 추가될 예정

        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 2)

    def populate_device_widgets(self, device_configs: dict):
        """Orchestrator로부터 장비 설정을 받아와 위젯을 동적으로 생성합니다."""
        for device_id, config in device_configs.items():
            widget = DeviceStatusWidget(
                device_id, config['host'], config['port']
            )
            self.device_widgets[device_id] = widget
            # 2열 그리드 레이아웃에 위젯 추가
            row, col = divmod(len(self.device_widgets) - 1, 2)
            self.device_grid_layout.addWidget(widget, row, col)

    @Slot(str, str, str)
    def on_agent_status_update(self, device_id: str, status: str, color: str):
        """Signal을 통해 전달받은 상태 정보로 UI를 업데이트하는 Slot."""
        log_message = f"[{device_id}] {status}"
        self.log_display.append(log_message)
        
        if device_id in self.device_widgets:
            self.device_widgets[device_id].update_status(status, color)
