# secs_simulator/ui/scenario_editor/property_editor.py

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFormLayout, QFrame,
    QComboBox, QDoubleSpinBox, QTreeWidget, QTreeWidgetItem,
    QPushButton, QMenu, QInputDialog, QMessageBox, QSpinBox
)
from PySide6.QtCore import Slot, Qt, Signal
import uuid
import copy

from .scenario_step_item import ScenarioStepItem
from secs_simulator.engine.scenario_manager import ScenarioManager


class PropertyEditor(QWidget):
    """'Send'와 'Wait' 액션을 모두 편집할 수 있는 속성 편집기입니다."""
    manual_send_requested = Signal(str, dict)

    def __init__(self, device_configs: dict, scenario_manager: ScenarioManager, parent=None):
        super().__init__(parent)
        self.device_configs = device_configs
        self.scenario_manager = scenario_manager
        self.current_item: ScenarioStepItem | None = None
        self.current_manual_message: dict | None = None
        self._is_internal_update = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # --- 공통 속성 ---
        layout.addWidget(QLabel("<b>Step Properties</b>"))
        self.form_layout = QFormLayout()
        self.device_id_combo = QComboBox()
        self.delay_spinbox = QDoubleSpinBox()
        self.delay_spinbox.setSuffix(" sec")
        self.action_type_combo = QComboBox()
        self.action_type_combo.addItems(["Send Message", "Wait for Reply"])

        self.form_layout.addRow("Action Type:", self.action_type_combo)
        self.form_layout.addRow("Device ID:", self.device_id_combo)
        self.form_layout.addRow("Delay Before:", self.delay_spinbox)
        layout.addLayout(self.form_layout)

        # --- 'Send' 액션 전용 위젯 ---
        self.send_panel = QWidget()
        send_layout = QVBoxLayout(self.send_panel)
        send_layout.setContentsMargins(0, 0, 0, 0)
        send_layout.addWidget(QLabel("<b>Message Body</b>"))
        self.message_body_tree = QTreeWidget()
        self.message_body_tree.setHeaderLabels(["Name", "Value"])
        send_layout.addWidget(self.message_body_tree)
        
        # --- 'Wait' 액션 전용 위젯 ---
        self.wait_panel = QWidget()
        wait_layout = QFormLayout(self.wait_panel)
        wait_layout.setContentsMargins(0, 5, 0, 0)
        wait_layout.addWidget(QLabel("<b>Wait Condition</b>"))
        self.wait_s_spinbox = QSpinBox()
        self.wait_f_spinbox = QSpinBox()
        self.wait_timeout_spinbox = QDoubleSpinBox()
        self.wait_s_spinbox.setRange(0, 255)
        self.wait_f_spinbox.setRange(0, 255)
        self.wait_timeout_spinbox.setRange(0.1, 300.0)
        self.wait_timeout_spinbox.setSuffix(" sec")
        wait_layout.addRow("Stream (S):", self.wait_s_spinbox)
        wait_layout.addRow("Function (F):", self.wait_f_spinbox)
        wait_layout.addRow("Timeout:", self.wait_timeout_spinbox)

        layout.addWidget(self.send_panel)
        layout.addWidget(self.wait_panel)
        layout.addStretch()

        # --- 수동 전송 버튼 ---
        self.send_now_button = QPushButton("🚀 Send Now")
        layout.addWidget(self.send_now_button)
        
        # --- Signal Connections ---
        self.action_type_combo.currentIndexChanged.connect(self.on_action_type_changed)
        self.device_id_combo.currentTextChanged.connect(self.on_device_id_changed)
        self.delay_spinbox.valueChanged.connect(self.on_delay_changed)
        self.message_body_tree.itemChanged.connect(self.on_message_body_item_changed)
        self.message_body_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.message_body_tree.customContextMenuRequested.connect(self._show_context_menu)
        self.wait_s_spinbox.valueChanged.connect(self.on_wait_condition_changed)
        self.wait_f_spinbox.valueChanged.connect(self.on_wait_condition_changed)
        self.wait_timeout_spinbox.valueChanged.connect(self.on_wait_condition_changed)
        self.send_now_button.clicked.connect(self.on_send_now_clicked)

        self.clear_view()
    
    # --- 헬퍼 함수들 (기존 코드와 유사, 일부 수정) ---
    def _find_item_by_id(self, data_list, target_id):
        for item in data_list:
            if item.get('id') == target_id: return item
            if item.get('type') == 'L':
                found = self._find_item_by_id(item.get('value', []), target_id)
                if found: return found
        return None

    def _remove_item_by_id(self, data_list, target_id):
        data_list[:] = [item for item in data_list if item.get('id') != target_id]
        for item in data_list:
            if item.get('type') == 'L':
                self._remove_item_by_id(item.get('value', []), target_id)

    def _ensure_ids(self, data_list):
        for item in data_list:
            if 'id' not in item: item['id'] = str(uuid.uuid4())
            if item.get('type') == 'L': self._ensure_ids(item.get('value', []))
            
    # --- UI Mode Control ---
    def clear_view(self):
        self._is_internal_update = True
        self.current_item = None
        self.current_manual_message = None
        
        self.action_type_combo.setCurrentIndex(0)
        self.device_id_combo.clear()
        self.delay_spinbox.setValue(0.0)
        self.message_body_tree.clear()
        self.wait_s_spinbox.setValue(0)
        self.wait_f_spinbox.setValue(0)
        self.wait_timeout_spinbox.setValue(10.0)

        # 패널 및 버튼 가시성 제어
        self.send_panel.show()
        self.wait_panel.hide()
        self.send_now_button.hide()
        self._is_internal_update = False

    @Slot(ScenarioStepItem)
    def display_step_properties(self, item: ScenarioStepItem):
        self._is_internal_update = True
        self.clear_view()
        self.current_item = item
        data = item.step_data

        # 1. 액션 타입 설정
        if 'wait_recv' in data:
            self.action_type_combo.setCurrentIndex(1) # Wait for Reply
        else:
            self.action_type_combo.setCurrentIndex(0) # Send Message

        # 2. 공통 필드 채우기
        self._populate_common_fields(data)

        # 3. 액션별 상세 필드 채우기
        if 'wait_recv' in data:
            self.wait_s_spinbox.setValue(data['wait_recv'].get('s', 0))
            self.wait_f_spinbox.setValue(data['wait_recv'].get('f', 0))
            self.wait_timeout_spinbox.setValue(data.get('timeout', 10.0))
        
        if 'message' in data:
            message_body = data.get('message', {}).get('body')
            if message_body is not None:
                self._ensure_ids(message_body)
                self._refresh_ui_from_model(message_body)
        
        self._is_internal_update = False

    @Slot(dict)
    def display_for_manual_send(self, message_data: dict):
        # 수동 전송은 항상 Send Message 액션
        self._is_internal_update = True
        self.clear_view()
        self.current_manual_message = copy.deepcopy(message_data.get("message"))
        
        self.action_type_combo.setEnabled(False) # 모드 변경 불가
        self.send_now_button.show()
        
        self._populate_common_fields(message_data)

        message_body = self.current_manual_message.get('body')
        if message_body is not None:
            self._ensure_ids(message_body)
            self._refresh_ui_from_model(message_body)
        
        self._is_internal_update = False
    
    def _populate_common_fields(self, data_source: dict):
        device_type = data_source.get("device_type")
        self.device_id_combo.clear()
        available_devices = [dev_id for dev_id, conf in self.device_configs.items() if conf.get('type') == device_type]
        self.device_id_combo.addItems(available_devices)
        
        current_device = data_source.get("device_id", "Select Device...")
        
        if len(available_devices) == 1 and current_device not in available_devices:
            current_device = available_devices[0]
            if self.current_item:
                self.current_item.step_data['device_id'] = current_device
                self.current_item.update_visuals()

        self.device_id_combo.setCurrentText(current_device)
        self.delay_spinbox.setValue(data_source.get("delay", 0.0))

    def _get_current_message_body(self):
        if self.current_item and 'message' in self.current_item.step_data:
            return self.current_item.step_data['message'].setdefault('body', [])
        if self.current_manual_message:
            return self.current_manual_message.setdefault('body', [])
        return None

    def _refresh_ui_from_model(self, message_body: list | None):
        self._is_internal_update = True
        self.message_body_tree.clear()
        if message_body is not None: self._populate_message_tree(self.message_body_tree, message_body)
        self.message_body_tree.expandAll()
        self._is_internal_update = False

    def _populate_message_tree(self, parent_widget, data_list):
        for item_data in data_list:
            tree_item = QTreeWidgetItem(parent_widget)
            tree_item.setData(0, Qt.ItemDataRole.UserRole, item_data)
            item_type, val = item_data.get('type'), item_data.get('value')
            if item_type == 'L':
                tree_item.setText(0, f"L[{len(val)}]")
                self._populate_message_tree(tree_item, val)
            else:
                tree_item.setText(0, item_type)
                tree_item.setText(1, str(val))
                tree_item.setFlags(tree_item.flags() | Qt.ItemIsEditable)

    # --- 컨텍스트 메뉴 및 데이터 조작 로직 (기존과 거의 동일) ---
    @Slot(object)
    def _show_context_menu(self, position):
        # ... (기존 코드와 동일)
        menu = QMenu()
        selected_item = self.message_body_tree.currentItem()
        add_action = menu.addAction("Add New Item")
        add_action.triggered.connect(lambda: self._add_item_action(selected_item))
        if selected_item:
            remove_action = menu.addAction("Remove Selected Item")
            remove_action.triggered.connect(lambda: self._remove_item_action(selected_item))
            change_type_action = menu.addAction("Change Type")
            change_type_action.triggered.connect(lambda: self._change_type_action(selected_item))
        menu.exec(self.message_body_tree.mapToGlobal(position))

    def _add_item_action(self, selected_item: QTreeWidgetItem | None):
        # ... (기존 코드와 동일)
        SECS_TYPES = ['L', 'A', 'B', 'U1', 'U2', 'U4', 'I1', 'I2', 'I4', 'F4', 'F8', 'BOOL']
        item_type, ok = QInputDialog.getItem(self, "Add SECS Item", "Select item type:", SECS_TYPES, 0, False)
        if not ok: return
        new_item_data = {'id': str(uuid.uuid4()), 'type': item_type, 'value': [] if item_type == 'L' else ('' if item_type in ['A', 'B'] else 0)}
        target_list = self._get_current_message_body()
        if selected_item:
            selected_data = selected_item.data(0, Qt.ItemDataRole.UserRole)
            if selected_data:
                root_list = self._get_current_message_body()
                real_data = self._find_item_by_id(root_list, selected_data.get('id'))
                if real_data and real_data.get('type') == 'L':
                    target_list = real_data['value']
                else:
                    parent_item = selected_item.parent()
                    if parent_item:
                        parent_data = parent_item.data(0, Qt.ItemDataRole.UserRole)
                        if parent_data:
                            real_parent = self._find_item_by_id(root_list, parent_data.get('id'))
                            if real_parent and real_parent.get('type') == 'L':
                                target_list = real_parent['value']
        if target_list is not None:
            target_list.append(new_item_data)
        self._sync_model_and_views()

    def _remove_item_action(self, selected_item: QTreeWidgetItem):
        # ... (기존 코드와 동일)
        reply = QMessageBox.question(self, "Confirm Removal", "Are you sure you want to remove this item?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No: return
        selected_data = selected_item.data(0, Qt.ItemDataRole.UserRole)
        if not selected_data or 'id' not in selected_data: return
        root_list = self._get_current_message_body()
        if root_list: self._remove_item_by_id(root_list, selected_data.get('id'))
        self._sync_model_and_views()

    def _change_type_action(self, selected_item: QTreeWidgetItem):
        # ... (기존 코드와 동일)
        selected_data = selected_item.data(0, Qt.ItemDataRole.UserRole)
        if not selected_data or 'id' not in selected_data: return
        root_list = self._get_current_message_body()
        real_data = self._find_item_by_id(root_list, selected_data.get('id'))
        if not real_data: return
        SECS_TYPES = ['L', 'A', 'B', 'U1', 'U2', 'U4', 'I1', 'I2', 'I4', 'F4', 'F8', 'BOOL']
        current_type_index = SECS_TYPES.index(real_data.get('type')) if real_data.get('type') in SECS_TYPES else 0
        new_type, ok = QInputDialog.getItem(self, "Change Item Type", "Select new type:", SECS_TYPES, current_type_index, False)
        if not ok or new_type == real_data.get('type'): return
        real_data['type'] = new_type
        if new_type == 'L': real_data['value'] = []
        elif new_type in ['A', 'B']: real_data['value'] = ''
        elif new_type == 'BOOL': real_data['value'] = False
        else: real_data['value'] = 0
        self._sync_model_and_views()
    
    def _sync_model_and_views(self):
        self._refresh_ui_from_model(self._get_current_message_body())
        if self.current_item: self.current_item.update_visuals()

    # --- Event Handlers / Slots ---
    @Slot(int)
    def on_action_type_changed(self, index):
        """액션 타입 콤보박스 변경 시 UI와 데이터 모델을 업데이트합니다."""
        if self._is_internal_update or not self.current_item: return
        
        # UI 패널 가시성 전환
        is_wait_action = (index == 1)
        self.wait_panel.setVisible(is_wait_action)
        self.send_panel.setVisible(not is_wait_action)
        self.delay_spinbox.setEnabled(not is_wait_action)

        # 데이터 모델 업데이트
        if is_wait_action:
            # 'Send' 관련 키를 삭제하고 'Wait' 키를 추가
            self.current_item.step_data.pop('message', None)
            self.current_item.step_data.pop('message_id', None)
            self.current_item.step_data['wait_recv'] = {
                's': self.wait_s_spinbox.value(),
                'f': self.wait_f_spinbox.value()
            }
            self.current_item.step_data['timeout'] = self.wait_timeout_spinbox.value()
        else:
            # 'Wait' 관련 키를 삭제하고 'Send' 키를 추가
            self.current_item.step_data.pop('wait_recv', None)
            self.current_item.step_data.pop('timeout', None)
            # 기본 메시지 구조를 다시 만들어줌
            self.current_item.step_data['message_id'] = "Custom Msg"
            self.current_item.step_data['message'] = {'s': 0, 'f': 0, 'body': []}
            self._refresh_ui_from_model(self.current_item.step_data['message']['body'])

        self.current_item.update_visuals()

    @Slot()
    def on_wait_condition_changed(self):
        """Wait 조건 스핀박스 값 변경 시 데이터 모델을 업데이트합니다."""
        if self._is_internal_update or not self.current_item: return
        if 'wait_recv' in self.current_item.step_data:
            self.current_item.step_data['wait_recv']['s'] = self.wait_s_spinbox.value()
            self.current_item.step_data['wait_recv']['f'] = self.wait_f_spinbox.value()
            self.current_item.step_data['timeout'] = self.wait_timeout_spinbox.value()
            self.current_item.update_visuals()

    # 나머지 Slot들 (기존과 거의 동일)
    @Slot(QTreeWidgetItem, int)
    def on_message_body_item_changed(self, item: QTreeWidgetItem, column: int):
        if self._is_internal_update or column != 1: return
        # ... (기존 로직)
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not item_data or item_data.get('type') == 'L' or 'id' not in item_data: return
        root_list = self._get_current_message_body()
        real_data = self._find_item_by_id(root_list, item_data.get('id'))
        if not real_data: return
        new_value_str, item_type = item.text(1), real_data.get('type')
        current_value = real_data.get('value')
        try:
            new_value = current_value
            if item_type in ['A', 'B']: new_value = new_value_str
            elif item_type in ['U1', 'U2', 'U4', 'I1', 'I2', 'I4']: new_value = int(new_value_str)
            elif item_type in ['F4', 'F8']: new_value = float(new_value_str)
            elif item_type == 'BOOL': new_value = new_value_str.lower() in ['true', '1', 't', 'y', 'yes']
            if new_value != current_value:
                real_data['value'] = new_value
                self.current_item.update_visuals()
        except (ValueError, TypeError):
            self._is_internal_update = True
            item.setText(1, str(current_value))
            self._is_internal_update = False

    @Slot(str)
    def on_device_id_changed(self, text: str):
        if self._is_internal_update or not self.current_item: return
        self.current_item.step_data['device_id'] = text
        self.current_item.update_visuals()

    @Slot(float)
    def on_delay_changed(self, value: float):
        if self._is_internal_update or not self.current_item: return
        self.current_item.step_data['delay'] = value
        self.current_item.update_visuals()

    @Slot()
    def on_send_now_clicked(self):
        device_id = self.device_id_combo.currentText()
        if not device_id or not self.current_manual_message:
            QMessageBox.warning(self, "Send Error", "Please select a valid device.")
            return
        self.manual_send_requested.emit(device_id, self.current_manual_message)