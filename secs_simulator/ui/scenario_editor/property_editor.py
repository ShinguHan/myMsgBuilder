from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFormLayout,
    QComboBox, QDoubleSpinBox, QTreeWidget, QTreeWidgetItem,
    QPushButton, QMenu, QInputDialog, QMessageBox
)
from PySide6.QtCore import Slot, Qt, Signal
import uuid
import copy

from .scenario_step_item import ScenarioStepItem
from secs_simulator.engine.scenario_manager import ScenarioManager


class PropertyEditor(QWidget):
    """스텝 편집 및 수동 메시지 전송을 위한 속성 편집기입니다."""
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
        layout.addWidget(QLabel("<b>Properties</b>"))
        
        self.form_layout = QFormLayout()
        self.device_id_combo = QComboBox()
        self.delay_spinbox = QDoubleSpinBox()
        self.delay_spinbox.setSuffix(" sec")
        
        self.message_body_tree = QTreeWidget()
        self.message_body_tree.setHeaderLabels(["Name", "Value"])
        
        self.send_now_button = QPushButton("🚀 Send Now")

        self.form_layout.addRow("Device ID:", self.device_id_combo)
        self.form_layout.addRow("Delay Before:", self.delay_spinbox)
        layout.addLayout(self.form_layout)
        layout.addWidget(QLabel("<b>Message Body</b>"))
        layout.addWidget(self.message_body_tree)
        layout.addStretch()
        layout.addWidget(self.send_now_button)

        # --- Signal Connections ---
        self.device_id_combo.currentTextChanged.connect(self.on_device_id_changed)
        self.delay_spinbox.valueChanged.connect(self.on_delay_changed)
        self.send_now_button.clicked.connect(self.on_send_now_clicked)
        self.message_body_tree.itemChanged.connect(self.on_message_body_item_changed)

        self.message_body_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.message_body_tree.customContextMenuRequested.connect(self._show_context_menu)
        
        self.clear_view()

    # --- 헬퍼 함수 ---
    def _find_item_by_id(self, data_list, target_id):
        """body 리스트 안에서 id로 항목을 찾아 반환 (재귀 탐색)."""
        for item in data_list:
            if item.get('id') == target_id:
                return item
            if item.get('type') == 'L' and isinstance(item.get('value'), list):
                found = self._find_item_by_id(item['value'], target_id)
                if found:
                    return found
        return None

    def _remove_item_by_id(self, data_list, target_id):
        """id로 항목을 찾아 삭제 (재귀 탐색)."""
        for idx, item in enumerate(data_list):
            if item.get('id') == target_id:
                data_list.pop(idx)
                return True
            if item.get('type') == 'L' and isinstance(item.get('value'), list):
                if self._remove_item_by_id(item['value'], target_id):
                    return True
        return False

    def _ensure_ids(self, data_list):
        """로드된 데이터에 ID가 없을 경우 재귀적으로 ID를 부여합니다."""
        for item in data_list:
            if 'id' not in item:
                item['id'] = str(uuid.uuid4())
            if item.get('type') == 'L' and isinstance(item.get('value'), list):
                self._ensure_ids(item['value'])

    # --- UI Mode Control ---
    def clear_view(self):
        self._is_internal_update = True
        self.current_item = None
        self.current_manual_message = None
        self.device_id_combo.clear()
        self.delay_spinbox.setValue(0)
        self.message_body_tree.clear()
        self.send_now_button.hide()
        self.form_layout.labelForField(self.delay_spinbox).show()
        self.delay_spinbox.show()
        self._is_internal_update = False

    @Slot(ScenarioStepItem)
    def display_step_properties(self, item: ScenarioStepItem):
        self._is_internal_update = True
        self.current_item = item
        self.current_manual_message = None
        data = item.step_data
        self.form_layout.labelForField(self.delay_spinbox).show()
        self.delay_spinbox.show()
        self.send_now_button.hide()
        self._populate_common_fields(data)
        self._is_internal_update = False

    @Slot(dict)
    def display_for_manual_send(self, message_data: dict):
        self._is_internal_update = True
        self.current_item = None
        self.current_manual_message = copy.deepcopy(message_data.get("message"))
        self.form_layout.labelForField(self.delay_spinbox).hide()
        self.delay_spinbox.hide()
        self.send_now_button.show()
        self._populate_common_fields(message_data)
        self._is_internal_update = False
    
    def _populate_common_fields(self, data_source: dict):
        device_type = data_source.get("device_type")
        self.device_id_combo.clear()
        
        available_devices = [
            dev_id for dev_id, conf in self.device_configs.items()
            if conf.get('type') == device_type
        ]
        self.device_id_combo.addItems(available_devices)

        current_device_id = data_source.get("device_id")
        
        # [핵심 수정] 자동 선택 로직을 더 명확하게 변경
        if len(available_devices) == 1 and current_device_id not in available_devices:
            new_device_id = available_devices[0]
            self.device_id_combo.setCurrentText(new_device_id)
            
            # 타임라인 스텝을 편집하는 경우, 데이터 모델을 즉시 업데이트합니다.
            if self.current_item:
                self.current_item.step_data["device_id"] = new_device_id
                self.current_item.update_visuals()
        else:
            # 자동 선택 조건이 아닐 경우, 기존 데이터의 값으로 UI를 설정합니다.
            self.device_id_combo.setCurrentText(current_device_id)

        self.delay_spinbox.setValue(data_source.get("delay", 0))

        message_body = self._get_current_message_body()
        if message_body is not None:
            self._ensure_ids(message_body)
        
        self._refresh_ui_from_model(message_body)
    
    # --- Data Model & UI Synchronization ---
    def _get_current_message_body(self) -> list | None:
        if self.current_item:
            message = self.current_item.step_data.setdefault("message", {})
            return message.setdefault("body", [])
        if self.current_manual_message:
            return self.current_manual_message.setdefault("body", [])
        return None

    def _refresh_ui_from_model(self, message_body: list | None):
        self._is_internal_update = True
        self.message_body_tree.clear()
        if message_body is not None:
            self._populate_message_tree(self.message_body_tree, message_body)
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

    # --- Context Menu Actions ---
    @Slot(object)
    def _show_context_menu(self, position):
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
        SECS_TYPES = ['L', 'A', 'B', 'U1', 'U2', 'U4',
                      'I1', 'I2', 'I4', 'F4', 'F8', 'BOOL']
        item_type, ok = QInputDialog.getItem(
            self, "Add SECS Item", "Select item type:", SECS_TYPES, 0, False
        )
        if not ok:
            return

        new_item_data = {
            'id': str(uuid.uuid4()),
            'type': item_type,
            'value': [] if item_type == 'L' else ('' if item_type in ['A', 'B'] else 0)
        }

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
        reply = QMessageBox.question(
            self, "Confirm Removal",
            "Are you sure you want to remove this item and all its children?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.No:
            return

        selected_data = selected_item.data(0, Qt.ItemDataRole.UserRole)
        if not selected_data or 'id' not in selected_data: # ID가 없는 데이터는 삭제하지 않도록 방어
            return

        root_list = self._get_current_message_body()
        if root_list:
            self._remove_item_by_id(root_list, selected_data.get('id'))

        self._sync_model_and_views()

    def _change_type_action(self, selected_item: QTreeWidgetItem):
        selected_data = selected_item.data(0, Qt.ItemDataRole.UserRole)
        if not selected_data or 'id' not in selected_data:
            return

        root_list = self._get_current_message_body()
        real_data = self._find_item_by_id(root_list, selected_data.get('id'))
        if not real_data:
            return

        SECS_TYPES = ['L', 'A', 'B', 'U1', 'U2', 'U4',
                      'I1', 'I2', 'I4', 'F4', 'F8', 'BOOL']
        current_type_index = SECS_TYPES.index(real_data.get('type')) if real_data.get('type') in SECS_TYPES else 0
        new_type, ok = QInputDialog.getItem(
            self, "Change Item Type", "Select new type:",
            SECS_TYPES, current_type_index, False
        )
        if not ok or new_type == real_data.get('type'):
            return

        real_data['type'] = new_type
        if new_type == 'L':
            real_data['value'] = []
        elif new_type in ['A', 'B']:
            real_data['value'] = ''
        elif new_type == 'BOOL':
            real_data['value'] = False
        else:
            real_data['value'] = 0

        self._sync_model_and_views()
    
    def _sync_model_and_views(self):
        self._refresh_ui_from_model(self._get_current_message_body())
        if self.current_item:
            self.current_item.update_visuals()

    # --- Event Handlers / Slots ---
    @Slot(QTreeWidgetItem, int)
    def on_message_body_item_changed(self, item: QTreeWidgetItem, column: int):
        if self._is_internal_update or column != 1:
            return

        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not item_data or item_data.get('type') == 'L' or 'id' not in item_data:
            return

        root_list = self._get_current_message_body()
        real_data = self._find_item_by_id(root_list, item_data.get('id'))
        if not real_data:
            return

        new_value_str, item_type = item.text(1), real_data.get('type')
        current_value = real_data.get('value')
        
        try:
            new_value = current_value
            if item_type in ['A', 'B']:
                new_value = new_value_str
            elif item_type in ['U1', 'U2', 'U4', 'I1', 'I2', 'I4']:
                new_value = int(new_value_str)
            elif item_type in ['F4', 'F8']:
                new_value = float(new_value_str)
            elif item_type == 'BOOL':
                new_value = new_value_str.lower() in ['true', '1', 't', 'y', 'yes']
            
            if new_value != current_value:
                real_data['value'] = new_value
                # 값 변경 시에는 전체 동기화 대신 해당 아이템만 업데이트
                self.current_item.update_visuals()
        except (ValueError, TypeError):
            self._is_internal_update = True
            item.setText(1, str(current_value))
            self._is_internal_update = False

    @Slot(str)
    def on_device_id_changed(self, text: str):
        if self._is_internal_update or not self.current_item:
            return
        self.current_item.step_data['device_id'] = text
        self.current_item.update_visuals()

    @Slot(float)
    def on_delay_changed(self, value: float):
        if self._is_internal_update or not self.current_item:
            return
        self.current_item.step_data['delay'] = value
        self.current_item.update_visuals()

    @Slot()
    def on_send_now_clicked(self):
        device_id = self.device_id_combo.currentText()
        if not device_id or not self.current_manual_message:
            QMessageBox.warning(self, "Send Error", "Please select a valid device.")
            return
        self.manual_send_requested.emit(device_id, self.current_manual_message)

