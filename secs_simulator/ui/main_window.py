# secs_simulator/ui/main_window.py
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFileDialog,
                               QPushButton, QScrollArea, QFrame, QMessageBox
                               )
from PySide6.QtCore import Signal, Slot, QEasingCurve, Qt, QPropertyAnimation, QParallelAnimationGroup
from PySide6.QtGui import QCursor
from typing import Dict
import asyncio
import json
import logging

from secs_simulator.engine.orchestrator import Orchestrator
from secs_simulator.ui.device_status_widget import DeviceStatusWidget
from secs_simulator.ui.scenario_editor.scenario_editor_widget import ScenarioEditorWidget
from secs_simulator.engine.scenario_manager import ScenarioManager
from secs_simulator.ui.add_device_dialog import AddDeviceDialog
from .log_viewer_window import LogViewerWindow


DEVICE_CONFIG_PATH = './secs_simulator/engine/devices.json'

class MainWindow(QMainWindow):
    agent_status_updated = Signal(str, str, str)

    def __init__(self, orchestrator: Orchestrator, shutdown_future: asyncio.Future):
        super().__init__()
        self.orchestrator = orchestrator
        self.shutdown_future = shutdown_future
        self.log_viewer_window = LogViewerWindow()
        device_configs = orchestrator.load_device_configs(DEVICE_CONFIG_PATH)
        self.scenario_manager = ScenarioManager(
            device_configs=device_configs,
            message_library_dir='./resources/messages'
        )
        self.device_widgets: Dict[str, DeviceStatusWidget] = {}
        self.selected_device_id: str | None = None

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

        self.left_panel = QFrame()
        self.left_panel.setObjectName("leftPanel")
        self.left_panel.setMinimumWidth(300)
        self.left_panel.setMaximumWidth(300)
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(10, 5, 10, 5)
        self.toggle_button = QPushButton("◀ Devices")
        self.toggle_button.clicked.connect(self.toggle_left_panel)
        self.toggle_button.setObjectName("toggleButton")
        self.toggle_button.setStyleSheet("padding: 8px 10px;")
        header_layout.addWidget(self.toggle_button)
        left_layout.addLayout(header_layout)
        
        self.collapsible_container = QWidget()
        collapsible_layout = QVBoxLayout(self.collapsible_container)
        collapsible_layout.setContentsMargins(10, 0, 10, 10)
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

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_content = QWidget()
        self.device_list_layout = QVBoxLayout(scroll_content)
        self.device_list_layout.setSpacing(10)
        self.device_list_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        
        # ✅ [레이아웃 수정 1] scroll_area가 collapsible_layout 내부에서 확장되도록 stretch factor(1)를 부여합니다.
        collapsible_layout.addWidget(scroll_area, 1)
        
        # ✅ [레이아웃 수정 2] collapsible_container가 left_layout 내부에서 확장되도록 stretch factor(1)를 부여합니다.
        left_layout.addWidget(self.collapsible_container, 1)
        
        management_frame = QFrame()
        management_frame.setObjectName("managementFrame")
        device_management_layout = QHBoxLayout(management_frame)
        device_management_layout.setContentsMargins(10, 5, 10, 10)
        
        add_button = QPushButton("➕ Add")
        edit_button = QPushButton("✏️ Edit")
        delete_button = QPushButton("🗑️ Delete")
        
        add_button.setToolTip("Add a new device configuration.")
        edit_button.setToolTip("Edit the selected device.")
        delete_button.setToolTip("Delete the selected device.")
        
        add_button.clicked.connect(self.add_new_device)
        edit_button.clicked.connect(self.edit_selected_device)
        delete_button.clicked.connect(self.delete_selected_device)

        device_management_layout.addWidget(add_button)
        device_management_layout.addWidget(edit_button)
        device_management_layout.addWidget(delete_button)

        # ✅ [레이아웃 수정 3] 불필요한 addStretch()를 제거하고 management_frame을 맨 아래에 추가합니다.
        left_layout.addWidget(management_frame)

        # --- Right Panel ---
        right_splitter = QWidget()
        right_layout = QVBoxLayout(right_splitter)
        self.editor_widget = ScenarioEditorWidget(self.scenario_manager, device_configs)
        
        scenario_control_layout = QHBoxLayout()
        load_button = QPushButton("📂 Load Scenario...")
        save_button = QPushButton("💾 Save Scenario...")
        self.run_button = QPushButton("▶ Run Edited Scenario")
        self.run_button.setStyleSheet("background-color: #3478F6; color: white; font-weight: bold;")
        self.show_log_button = QPushButton("📄 Show Logs")
        self.show_log_button.clicked.connect(self.log_viewer_window.show)

        load_button.clicked.connect(self.load_scenario_from_file)
        save_button.clicked.connect(self.save_scenario_to_file)
        self.run_button.clicked.connect(self.run_edited_scenario)
        scenario_control_layout.addWidget(load_button)
        scenario_control_layout.addWidget(save_button)
        scenario_control_layout.addStretch()
        scenario_control_layout.addWidget(self.show_log_button)
        scenario_control_layout.addWidget(self.run_button)

        right_layout.addWidget(self.editor_widget)
        right_layout.addLayout(scenario_control_layout)

        main_layout.addWidget(self.left_panel)
        main_layout.addWidget(right_splitter, 1)
        self.editor_widget.manual_send_requested.connect(self.orchestrator.send_single_message)

    def toggle_left_panel(self):
        start_width = self.left_panel.width()
        is_collapsing = start_width > 50
        end_width = 50 if is_collapsing else 300

        self.collapsible_container.setVisible(True)
        # ✅ [레이아웃 수정 4] 패널 하단 버튼 프레임도 함께 접히도록 로직에 추가
        management_frame = self.left_panel.findChild(QFrame, "managementFrame")
        if management_frame:
            management_frame.setVisible(True)

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
        
        self.animation_group.start()

        if is_collapsing:
            self.toggle_button.setText("▶")
            self.collapsible_container.setVisible(False)
            if management_frame:
                management_frame.setVisible(False)
        else:
            self.toggle_button.setText("◀ Devices")

    def start_agents(self):
        logging.info("--- Starting all agents... ---")
        asyncio.create_task(self.orchestrator.start_all_agents())
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

    def stop_agents(self):
        logging.info("--- Stopping all agents... ---")
        asyncio.create_task(self.orchestrator.stop_all_agents())
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def closeEvent(self, event):
        if not self.shutdown_future.done():
            self.shutdown_future.set_result(True)
        event.accept()

    def populate_device_widgets(self, device_configs: dict):
        for i in reversed(range(self.device_list_layout.count() -1)):
            widget_to_remove = self.device_list_layout.itemAt(i).widget()
            if widget_to_remove:
                widget_to_remove.setParent(None)
        self.device_widgets.clear()
        
        self.selected_device_id = None

        for device_id, config in device_configs.items():
            if device_id not in self.device_widgets:
                widget = DeviceStatusWidget(
                    device_id, 
                    config['host'], 
                    config['port'],
                    config.get('connection_mode', 'Passive')
                )
                widget.toggled.connect(self.on_device_toggled)
                widget.mousePressEvent = lambda event, dev_id=device_id: self._on_device_selected(dev_id, event)
                self.device_widgets[device_id] = widget
                self.device_list_layout.insertWidget(self.device_list_layout.count() - 1, widget)

    @Slot(str)
    def _on_device_selected(self, device_id: str, event):
        for dev_id, widget in self.device_widgets.items():
            is_selected = (dev_id == device_id)
            if is_selected:
                widget.setStyleSheet("#statusCard { border: 1.5px solid #3478F6; }")
            else:
                widget.setStyleSheet("")

        self.selected_device_id = device_id
        logging.debug(f"Device '{self.selected_device_id}' selected.")
        QFrame.mousePressEvent(self.device_widgets[device_id], event)

    @Slot(str, str, str)
    def on_agent_status_update(self, device_id: str, status: str, color: str):        
        if device_id in self.device_widgets:
            is_active = "Stopped" not in status
            self.device_widgets[device_id].update_status(status, color, is_active)

    @Slot(str, bool)
    def on_device_toggled(self, device_id: str, is_on: bool):
        if is_on:
            asyncio.create_task(self.orchestrator.start_agent(device_id))
        else:
            asyncio.create_task(self.orchestrator.stop_agent(device_id))
    
    def add_new_device(self):
        dialog = AddDeviceDialog(self)
        if dialog.exec():
            device_info = dialog.get_device_info()
            if device_info:
                device_id = device_info.pop("id")
                
                success = self.orchestrator.add_device(device_id, device_info)
                if success:
                    new_configs = self.orchestrator.load_device_configs(DEVICE_CONFIG_PATH)
                    self.populate_device_widgets(new_configs)
                    logging.info(f"--- Device '{device_id}' added successfully. ---")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to add device '{device_id}'. The ID might already exist.")

    def edit_selected_device(self):
        if not self.selected_device_id:
            QMessageBox.information(self, "Edit Device", "Please select a device to edit from the list.")
            return

        config = self.orchestrator._device_configs.get(self.selected_device_id)
        if not config: return

        dialog = AddDeviceDialog(self)
        dialog.setWindowTitle("Edit Device")
        dialog.id_input.setText(self.selected_device_id)
        dialog.type_input.setCurrentText(config.get('type', ''))
        dialog.connection_mode_input.setCurrentText(config.get('connection_mode', 'Passive'))
        dialog.host_input.setText(config.get('host', '127.0.0.1'))
        dialog.port_input.setValue(config.get('port', 5000))
        dialog.t3_input.setValue(config.get('t3', 10))
        dialog.t5_input.setValue(config.get('t5', 10))
        dialog.t6_input.setValue(config.get('t6', 5))
        dialog.t7_input.setValue(config.get('t7', 10))
        
        if dialog.exec():
            new_info = dialog.get_device_info()
            if new_info:
                new_device_id = new_info.pop("id")
                asyncio.create_task(self._edit_and_refresh(self.selected_device_id, new_device_id, new_info))

    async def _edit_and_refresh(self, old_id, new_id, config):
        await self.orchestrator.edit_device(old_id, new_id, config)
        new_configs = self.orchestrator.load_device_configs(DEVICE_CONFIG_PATH)
        self.populate_device_widgets(new_configs)
        logging.info(f"--- Device '{old_id}' was updated to '{new_id}'. ---")

    def delete_selected_device(self):
        if not self.selected_device_id:
            QMessageBox.information(self, "Delete Device", "Please select a device to delete from the list.")
            return

        reply = QMessageBox.question(
            self, "Confirm Deletion",
            f"Are you sure you want to delete the device '{self.selected_device_id}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            asyncio.create_task(self._delete_and_refresh(self.selected_device_id))

    async def _delete_and_refresh(self, device_id_to_delete):
        await self.orchestrator.delete_device(device_id_to_delete)
        new_configs = self.orchestrator.load_device_configs(DEVICE_CONFIG_PATH)
        self.populate_device_widgets(new_configs)
        logging.info(f"--- Device '{device_id_to_delete}' was deleted. ---")
        self.selected_device_id = None

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
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Master Scenario", "./resources/scenarios", "JSON Files (*.json)")
        if not file_path: return

        scenario_data = self.editor_widget.export_to_master_scenario()
        success = self.scenario_manager.save_scenario(scenario_data, file_path)
        if success:
            logging.info(f"--- Scenario saved to {file_path} ---")
        else:
            logging.error(f"--- Failed to save scenario. ---")
            
    def load_scenario_from_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Load Master Scenario", "./resources/scenarios", "JSON Files (*.json)")
        if not file_path: return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                scenario_data = json.load(f)
            self.editor_widget.load_from_scenario_data(scenario_data)
            logging.info(f"--- Scenario loaded from {file_path} ---")
        except Exception as e:
            logging.error(f"--- Error loading scenario: {e} ---")