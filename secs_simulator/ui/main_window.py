from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFileDialog,
                               QPushButton, QTextEdit, QScrollArea, QFrame, QMenu
                               )
from PySide6.QtCore import Signal, Slot, QEasingCurve, Qt,QPropertyAnimation, QParallelAnimationGroup
from PySide6.QtGui import QCursor
from typing import Dict
import asyncio
import json
import logging # logging 모듈 임포트

from secs_simulator.engine.orchestrator import Orchestrator
from secs_simulator.ui.device_status_widget import DeviceStatusWidget
from secs_simulator.ui.scenario_editor.scenario_editor_widget import ScenarioEditorWidget
from secs_simulator.engine.scenario_manager import ScenarioManager
from secs_simulator.ui.add_device_dialog import AddDeviceDialog

from secs_simulator.ui.log_viewer import LogViewer # 새로 만든 LogViewer 임포트


DEVICE_CONFIG_PATH = './secs_simulator/engine/devices.json'

class MainWindow(QMainWindow):
    agent_status_updated = Signal(str, str, str)

    def __init__(self, orchestrator: Orchestrator, shutdown_future: asyncio.Future):
        super().__init__()
        self.orchestrator = orchestrator
        self.shutdown_future = shutdown_future
        
        # 2. ✅ [핵심 수정] 장비 설정 파일을 먼저 로드합니다.
        # main.py가 있는 위치 기준으로 상대 경로를 지정합니다.
        device_configs = orchestrator.load_device_configs(DEVICE_CONFIG_PATH)

        
        self.scenario_manager = ScenarioManager(
            device_configs=device_configs,
            message_library_dir='./resources/messages'
        )
        self.device_widgets: Dict[str, DeviceStatusWidget] = {}

        self.setWindowTitle("SECS/HSMS Multi-Device Simulator")
        self.setGeometry(100, 100, 1600, 900)
        self.agent_status_updated.connect(self.on_agent_status_update)
        self._init_ui(device_configs)
        self.load_and_populate_libraries()
        self.populate_device_widgets(device_configs)

    def _init_ui(self, device_configs: dict):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        # --- Left Panel ---
        self.left_panel = QFrame()
        self.left_panel.setObjectName("leftPanel")
        self.left_panel.setMinimumWidth(300)
        self.left_panel.setMaximumWidth(300)

        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # 1. 패널 숨김 버튼 추가
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(10, 5, 10, 5)
        self.toggle_button = QPushButton("◀ Devices")
        self.toggle_button.clicked.connect(self.toggle_left_panel)
        self.toggle_button.setObjectName("toggleButton")
        self.toggle_button.setStyleSheet("padding: 8px 10px;")
        header_layout.addWidget(self.toggle_button)
        # ✅ [수정] 버튼을 찌그러뜨리던 불필요한 Stretch 제거
        left_layout.addLayout(header_layout)
        
        self.collapsible_container = QWidget()
        collapsible_layout = QVBoxLayout(self.collapsible_container)
        collapsible_layout.setContentsMargins(10, 0, 10, 0)
        collapsible_layout.setSpacing(10)

        control_layout = QHBoxLayout()
        self.start_button = QPushButton("🚀 Start All")
        self.stop_button = QPushButton("⏹️ Stop All")
        self.stop_button.setEnabled(False)
        self.start_button.clicked.connect(self.start_agents)
        self.stop_button.clicked.connect(self.stop_agents)
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)
        collapsible_layout.addLayout(control_layout)

        # 디바이스 목록 (세로 정렬)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        self.device_list_layout = QVBoxLayout(scroll_content)
        self.device_list_layout.setSpacing(10)
        self.device_list_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        collapsible_layout.addWidget(scroll_area)
        
        left_layout.addWidget(self.collapsible_container)
        
        # ✅ [수정] 모든 위젯을 상단으로 밀어 올리는 Stretch 추가
        left_layout.addStretch()

        scroll_content.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        scroll_content.customContextMenuRequested.connect(self.show_device_context_menu)
        
        # --- Right Panel ---
        right_splitter = QWidget()
        right_layout = QVBoxLayout(right_splitter)
        self.editor_widget = ScenarioEditorWidget(self.scenario_manager, device_configs)
        
        self.log_viewer  = LogViewer()
        # self.log_display.setReadOnly(True)
        editor_log_splitter = QVBoxLayout()
        editor_log_splitter.addWidget(self.editor_widget, 3)
        editor_log_splitter.addWidget(self.log_viewer, 1)
        
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

        main_layout.addWidget(self.left_panel)
        main_layout.addWidget(right_splitter, 1)
        self.editor_widget.manual_send_requested.connect(self.orchestrator.send_single_message)

    def toggle_left_panel(self):
        start_width = self.left_panel.width()
        is_collapsing = start_width > 50
        end_width = 50 if is_collapsing else 300

        if not is_collapsing:
            self.collapsible_container.setVisible(True)

        self.animation_group = QParallelAnimationGroup(self)
        anim_max = QPropertyAnimation(self.left_panel, b"maximumWidth")
        anim_max.setDuration(300)
        anim_max.setStartValue(start_width)
        anim_max.setEndValue(end_width)
        anim_max.setEasingCurve(QEasingCurve.Type.InOutQuart)
        
        anim_min = QPropertyAnimation(self.left_panel, b"minimumWidth")
        anim_min.setDuration(300)
        anim_min.setStartValue(start_width)
        anim_min.setEndValue(end_width)
        anim_min.setEasingCurve(QEasingCurve.Type.InOutQuart)
        
        self.animation_group.addAnimation(anim_max)
        self.animation_group.addAnimation(anim_min)
        
        def on_animation_finished():
            if is_collapsing:
                self.collapsible_container.setVisible(False)

        self.animation_group.finished.connect(on_animation_finished)
        self.animation_group.start()

        if is_collapsing:
            self.toggle_button.setText("▶")
        else:
            self.toggle_button.setText("◀ Devices")

    def start_agents(self):
        logging.info("--- Starting all agents... ---") # append -> logging.info
        asyncio.create_task(self.orchestrator.start_all_agents())
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def stop_agents(self):
        logging.info("--- Stopping all agents... ---") # append -> logging.info
        asyncio.create_task(self.orchestrator.stop_all_agents())
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def closeEvent(self, event):
        if not self.shutdown_future.done():
            self.shutdown_future.set_result(True)
        event.accept()

    def populate_device_widgets(self, device_configs: dict):
        # 기존 위젯 클리어
        for i in reversed(range(self.device_list_layout.count() -1)):
            widget_to_remove = self.device_list_layout.itemAt(i).widget()
            if widget_to_remove:
                widget_to_remove.setParent(None)
        self.device_widgets.clear()

        # 새 설정으로 위젯 재생성
        for device_id, config in device_configs.items():
            if device_id not in self.device_widgets:
                # ✅ [버그 수정] DeviceStatusWidget 생성자에 connection_mode 인자를 전달합니다.
                widget = DeviceStatusWidget(
                    device_id, 
                    config['host'], 
                    config['port'],
                    config.get('connection_mode', 'Passive') # 기본값으로 'Passive' 사용
                )
                widget.toggled.connect(self.on_device_toggled) # 2. 개별 On/Off
                self.device_widgets[device_id] = widget
                self.device_list_layout.insertWidget(self.device_list_layout.count() - 1, widget)

    @Slot(str, str, str)
    def on_agent_status_update(self, device_id: str, status: str, color: str):        
        if device_id in self.device_widgets:
            # ✅ [버그 수정] 'Stopped'가 아닐 경우 모두 활성 상태로 간주하여 안정성 향상
            is_active = "Stopped" not in status
            self.device_widgets[device_id].update_status(status, color, is_active)

    @Slot(str, bool)
    def on_device_toggled(self, device_id: str, is_on: bool):
        if is_on:
            asyncio.create_task(self.orchestrator.start_agent(device_id))
        else:
            asyncio.create_task(self.orchestrator.stop_agent(device_id))

    def show_device_context_menu(self, position):
        menu = QMenu()
        add_action = menu.addAction("➕ Add New Device")
        action = menu.exec(QCursor.pos())
        if action == add_action:
            self.add_new_device()

    def add_new_device(self):
        dialog = AddDeviceDialog(self)
        if dialog.exec():
            device_info = dialog.get_device_info()
            if device_info:
                device_id = device_info["id"]
                # ✅ [버그 수정] connection_mode를 config에 포함하여 전달
                config = {
                    "host": device_info["host"],
                    "port": device_info["port"],
                    "type": device_info["type"],
                    "connection_mode": device_info["connection_mode"]
                }
                
                # Orchestrator에 추가 및 파일 저장
                success = self.orchestrator.add_device(device_id, config)
                if success:
                    # UI 갱신
                    new_configs = self.orchestrator.load_device_configs(DEVICE_CONFIG_PATH)
                    self.populate_device_widgets(new_configs)
                    logging.info(f"--- Device '{device_id}' added successfully. ---")
                else:
                    logging.error(f"--- Failed to add device '{device_id}'. Check logs. ---")

    def load_and_populate_libraries(self):
        all_libs = self.scenario_manager.get_all_message_libraries()
        self.editor_widget.library_view.populate(all_libs)

    def run_edited_scenario(self):
        scenario_data = self.editor_widget.export_to_scenario_data()
        if not scenario_data or not scenario_data.get("steps"):
            logging.warning("--- Scenario is empty. Add steps to the timeline. ---")
            return
            
        logging.info(f"--- Running scenario '{scenario_data['name']}'... ---")
        self.orchestrator.run_scenario(scenario_data)

    def save_scenario_to_file(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Master Scenario", "./resources/scenarios", "JSON Files (*.json)"
        )
        if not file_path: return

        scenario_data = self.editor_widget.export_to_master_scenario()
        success = self.scenario_manager.save_scenario(scenario_data, file_path)
        if success:
            logging.info(f"--- Scenario saved to {file_path} ---")
        else:
            logging.error(f"--- Failed to save scenario. ---")
            
    def load_scenario_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Master Scenario", "./resources/scenarios", "JSON Files (*.json)"
        )
        if not file_path: return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                scenario_data = json.load(f)
            self.editor_widget.load_from_scenario_data(scenario_data)
            logging.info(f"--- Scenario loaded from {file_path} ---")
        except Exception as e:
            logging.error(f"--- Error loading scenario: {e} ---")
