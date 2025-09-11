from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFileDialog,
                               QPushButton, QGridLayout, QTextEdit, QScrollArea)
from PySide6.QtCore import Signal, Slot
from typing import Dict
import asyncio
import json

from secs_simulator.engine.orchestrator import Orchestrator
from secs_simulator.ui.device_status_widget import DeviceStatusWidget
from secs_simulator.ui.scenario_editor.scenario_editor_widget import ScenarioEditorWidget
from secs_simulator.engine.scenario_manager import ScenarioManager

class MainWindow(QMainWindow):
    agent_status_updated = Signal(str, str, str)

    def __init__(self, orchestrator: Orchestrator):
        super().__init__()
        self.orchestrator = orchestrator
        
        device_configs = self.orchestrator.get_device_configs()
        
        self.scenario_manager = ScenarioManager(
            device_configs=device_configs,
            message_library_dir='./resources/messages'
        )
        self.device_widgets: Dict[str, DeviceStatusWidget] = {}

        self.setWindowTitle("SECS/HSMS Multi-Device Simulator")
        self.setGeometry(100, 100, 1200, 800)
        self.agent_status_updated.connect(self.on_agent_status_update)
        self._init_ui(device_configs)
        self.load_and_populate_libraries()
        self.populate_device_widgets(device_configs)

    def _init_ui(self, device_configs: dict):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # --- Left Panel ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        control_layout = QHBoxLayout()
        self.start_button = QPushButton("🚀 Start All Agents")
        self.stop_button = QPushButton("⏹️ Stop All Agents")
        self.stop_button.setEnabled(False)
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
        
        # --- Right Panel ---
        right_splitter = QWidget()
        right_layout = QVBoxLayout(right_splitter)
        self.editor_widget = ScenarioEditorWidget(self.scenario_manager, device_configs)
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        editor_log_splitter = QVBoxLayout()
        editor_log_splitter.addWidget(self.editor_widget, 3)
        editor_log_splitter.addWidget(self.log_display, 1)
        
        scenario_control_layout = QHBoxLayout()
        load_button = QPushButton("📂 Load Scenario...")
        save_button = QPushButton("💾 Save Scenario...")
        self.run_button = QPushButton("▶ Run Edited Scenario")
        self.run_button.setStyleSheet("background-color: #3478F6; color: white; font-weight: bold;")
        load_button.clicked.connect(self.load_scenario_from_file)
        save_button.clicked.connect(self.save_scenario_to_file)
        self.run_button.clicked.connect(self.run_edited_scenario)
        scenario_control_layout.addWidget(load_button)
        scenario_control_layout.addWidget(save_button)
        scenario_control_layout.addStretch()
        scenario_control_layout.addWidget(self.run_button)

        right_layout.addLayout(editor_log_splitter)
        right_layout.addLayout(scenario_control_layout)

        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_splitter, 3)

        # ✅ [9장 추가] EditorWidget의 수동 전송 요청을 Orchestrator의 슬롯에 연결
        self.editor_widget.manual_send_requested.connect(self.orchestrator.send_single_message)

    def start_agents(self):
        self.log_display.append("--- Starting all agents... ---")
        asyncio.create_task(self.orchestrator.start_all_agents())
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def stop_agents(self):
        self.log_display.append("--- Stopping all agents... ---")
        asyncio.create_task(self.orchestrator.stop_all_agents())
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def closeEvent(self, event):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.orchestrator.stop_all_agents())
        event.accept()

    def populate_device_widgets(self, device_configs: dict):
        col_count = 0
        for device_id, config in device_configs.items():
            if device_id not in self.device_widgets:
                widget = DeviceStatusWidget(device_id, config['host'], config['port'])
                self.device_widgets[device_id] = widget
                row, col = divmod(col_count, 2)
                self.device_grid_layout.addWidget(widget, row, col)
                col_count += 1

    @Slot(str, str, str)
    def on_agent_status_update(self, device_id: str, status: str, color: str):
        log_message = f"[{device_id}] {status}"
        self.log_display.append(log_message)
        if device_id in self.device_widgets:
            self.device_widgets[device_id].update_status(status, color)

    def load_and_populate_libraries(self):
        all_libs = self.scenario_manager.get_all_message_libraries()
        self.editor_widget.library_view.populate(all_libs)

    def run_edited_scenario(self):
        if not self.stop_button.isEnabled():
            self.log_display.append("--- Please start agents before running a scenario. ---")
            return
        
        scenario_data = self.editor_widget.export_to_scenario_data()
        if not scenario_data or not scenario_data.get("steps"):
            self.log_display.append("--- Scenario is empty. Add steps to the timeline. ---")
            return
            
        self.log_display.append(f"--- Running scenario '{scenario_data['name']}'... ---")
        self.orchestrator.run_scenario(scenario_data)

    def save_scenario_to_file(self):
        """시나리오를 파일로 저장하는 파일 대화상자를 엽니다."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Master Scenario", "./resources/scenarios", "JSON Files (*.json)"
        )
        if not file_path: return

        scenario_data = self.editor_widget.export_to_master_scenario()
        success = self.scenario_manager.save_scenario(scenario_data, file_path)
        if success:
            self.log_display.append(f"--- Scenario saved to {file_path} ---")
        else:
            self.log_display.append(f"--- Failed to save scenario. ---")
            
    def load_scenario_from_file(self):
        """파일에서 시나리오를 불러오는 파일 대화상자를 엽니다."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Master Scenario", "./resources/scenarios", "JSON Files (*.json)"
        )
        if not file_path: return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                scenario_data = json.load(f)
            self.editor_widget.load_from_scenario_data(scenario_data)
            self.log_display.append(f"--- Scenario loaded from {file_path} ---")
        except Exception as e:
            self.log_display.append(f"--- Error loading scenario: {e} ---")

