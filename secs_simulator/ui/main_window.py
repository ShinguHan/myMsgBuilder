from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFileDialog,
                               QPushButton, QGridLayout, QTextEdit, QScrollArea)
from PySide6.QtCore import Signal, Slot, QObject
from typing import Dict

from secs_simulator.engine.orchestrator import Orchestrator
from secs_simulator.ui.device_status_widget import DeviceStatusWidget
from secs_simulator.ui.scenario_editor_widget import ScenarioEditorWidget
from secs_simulator.engine.scenario_manager import ScenarioManager # ScenarioManager 임포트
import asyncio # 추가

class MainWindow(QMainWindow):
    """애플리케이션의 메인 윈도우 클래스."""
    
    # 백그라운드(asyncio) 스레드에서 UI를 안전하게 업데이트하기 위한 Signal
    # str, str, str -> device_id, status_message, color
    agent_status_updated = Signal(str, str, str)

    def __init__(self, orchestrator: Orchestrator):
        super().__init__()
        self.orchestrator = orchestrator
        # ✅ ScenarioManager 인스턴스 생성
        self.scenario_manager = ScenarioManager(
            device_configs=self.orchestrator.get_device_configs(),
            message_library_dir='./resources/messages'
        )
        self.device_widgets: Dict[str, DeviceStatusWidget] = {}

        self.setWindowTitle("SECS/HSMS Multi-Device Simulator")
        self.setGeometry(100, 100, 1200, 800)

        # Signal과 Slot을 연결
        self.agent_status_updated.connect(self.on_agent_status_update)

        self._init_ui()

        # ✅ UI 초기화 후 라이브러리 로드
        self.load_and_populate_libraries()

    def _init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # --- 왼쪽: 장비 상태 패널 ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        control_layout = QHBoxLayout()
        self.start_button = QPushButton("🚀 Start All Agents")
        self.stop_button = QPushButton("⏹️ Stop All Agents")
        self.stop_button.setEnabled(False)

        # ✅ 버튼 클릭 시그널을 해당 메소드에 연결
        self.start_button.clicked.connect(self.start_agents)
        self.stop_button.clicked.connect(self.stop_agents)

        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)
        left_layout.addLayout(control_layout)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        self.device_grid_layout = QGridLayout(scroll_content)
        scroll_area.setWidget(scroll_content)
        left_layout.addWidget(scroll_area)
        
        # --- ✅ 오른쪽: 로그 패널을 시나리오 편집기로 교체 ---
        right_splitter = QWidget()
        right_layout = QVBoxLayout(right_splitter)

        self.editor_widget = ScenarioEditorWidget() # 편집기 위젯 생성
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)

        # 편집기와 로그창을 위아래로 분할
        editor_log_splitter = QVBoxLayout()
        editor_log_splitter.addWidget(self.editor_widget, 3) # 편집기가 3의 비율
        editor_log_splitter.addWidget(self.log_display, 1)   # 로그가 1의 비율
        
        # 시나리오 제어 버튼 추가
        scenario_control_layout = QHBoxLayout()
        self.run_scenario_button = QPushButton("📂 Load & Run Scenario...")
        self.run_scenario_button.clicked.connect(self.load_and_run_scenario)
        scenario_control_layout.addWidget(self.run_scenario_button)
        scenario_control_layout.addStretch()

        right_layout.addLayout(editor_log_splitter)
        right_layout.addLayout(scenario_control_layout)

        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_splitter, 3) # 비율 조정

    # ✅ 아래 메소드들을 클래스에 추가
    def start_agents(self):
        """'Start All Agents' 버튼 클릭 시 실행될 슬롯."""
        self.log_display.append("--- Starting all agents... ---")
        # asyncio.create_task를 사용해 UI 멈춤 없이 비동기 함수를 실행
        asyncio.create_task(self.orchestrator.start_all_agents())
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def stop_agents(self):
        """'Stop All Agents' 버튼 클릭 시 실행될 슬롯."""
        self.log_display.append("--- Stopping all agents... ---")
        asyncio.create_task(self.orchestrator.stop_all_agents())
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def closeEvent(self, event):
        """윈도우가 닫힐 때 모든 에이전트를 확실히 종료시킵니다."""
        print("Closing application, stopping all agents...")
        # stop_agents가 비동기라 바로 종료하면 안되므로, loop에서 실행
        loop = asyncio.get_event_loop()
        # loop.create_task(self.orchestrator.stop_all_agents()) # 더 나은 방식
        loop.run_until_complete(self.orchestrator.stop_all_agents())
        event.accept()

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

    # ✅ 아래 두 메소드를 클래스에 추가
    def load_and_populate_libraries(self):
        """ScenarioManager를 통해 라이브러리를 로드하고 UI에 채웁니다."""
        all_libs = self.scenario_manager.get_all_message_libraries()
        self.editor_widget.library_view.populate(all_libs)

    def load_and_run_scenario(self):
        """파일 대화상자를 열어 시나리오를 선택하고 실행합니다."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Master Scenario", "./resources/scenarios", "JSON Files (*.json)"
        )
        if not file_path:
            return

        self.log_display.append(f"--- Loading scenario: {file_path} ---")
        scenario_data = self.scenario_manager.prepare_scenario(file_path)

        if scenario_data:
            self.log_display.append(f"--- Running scenario '{scenario_data.get('name', '')}' ---")
            self.orchestrator.run_scenario(scenario_data)
        else:
            self.log_display.append("--- Failed to load or prepare scenario. ---")
            
