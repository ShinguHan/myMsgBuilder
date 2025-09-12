# secs_simulator/ui/scenario_editor/property_editor.py
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFormLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QComboBox, QDoubleSpinBox, QSpinBox,
    QStyledItemDelegate, QHBoxLayout
)
from PySide6.QtCore import Slot, Qt, Signal
import uuid
import copy

from .scenario_step_item import ScenarioStepItem
from secs_simulator.engine.scenario_manager import ScenarioManager

# ✅ 3. 타입 변경 UI 오류 해결
class SecsTypeDelegate(QStyledItemDelegate):
    SECS_TYPES = ['L', 'A', 'B', 'U1', 'U2', 'U4', 'I1', 'I2', 'I4', 'F4', 'F8', 'BOOL']
    
    def createEditor(self, parent, option, index):
        if index.column() == 0:
            editor = QComboBox(parent)
            editor.addItems(self.SECS_TYPES)
            # 글자가 안보이던 문제 해결
            editor.setStyleSheet("padding: 2px; background-color: #3E3E3E;")
            # 선택 항목이 3개만 보이던 문제 해결
            editor.setMaxVisibleItems(len(self.SECS_TYPES))
            return editor
        return super().createEditor(parent, option, index)

    def setEditorData(self, editor, index):
        if isinstance(editor, QComboBox):
            value = index.model().data(index, Qt.ItemDataRole.EditRole).split('[')[0].strip()
            editor.setCurrentText(value)
        else:
            super().setEditorData(editor, index)

    def setModelData(self, editor, model, index):
        if isinstance(editor, QComboBox):
            model.setData(index, editor.currentText(), Qt.ItemDataRole.EditRole)
        else:
            super().setModelData(editor, model, index)

class PropertyEditor(QWidget):
    # ... (초기화 및 다른 함수들은 이전과 대부분 동일)
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
        self.send_panel = QWidget()
        send_layout = QVBoxLayout(self.send_panel)
        send_layout.setContentsMargins(0, 0, 0, 0)
        send_layout.addWidget(QLabel("<b>Message Body</b>"))
        self.message_body_tree = QTreeWidget()
        self.message_body_tree.setHeaderLabels(["Name", "Value", "Actions"])
        self.message_body_tree.setItemDelegateForColumn(0, SecsTypeDelegate(self))
        self.add_root_item_button = QPushButton("➕ Add Root Item")
        send_layout.addWidget(self.add_root_item_button)
        send_layout.addWidget(self.message_body_tree)
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
        layout.addWidget(self.send_panel, 1)
        layout.addWidget(self.wait_panel)
        self.send_now_button = QPushButton("🚀 Send Now")
        layout.addWidget(self.send_now_button)
        self.action_type_combo.currentIndexChanged.connect(self.on_action_type_changed)
        self.device_id_combo.currentTextChanged.connect(self.on_device_id_changed)
        self.delay_spinbox.valueChanged.connect(self.on_delay_changed)
        self.message_body_tree.itemChanged.connect(self.on_message_body_item_changed)
        self.wait_s_spinbox.valueChanged.connect(self.on_wait_condition_changed)
        self.wait_f_spinbox.valueChanged.connect(self.on_wait_condition_changed)
        self.wait_timeout_spinbox.valueChanged.connect(self.on_wait_condition_changed)
        self.send_now_button.clicked.connect(self.on_send_now_clicked)
        self.add_root_item_button.clicked.connect(self._add_root_item_action)
        self.clear_view()
    
    # ... (데이터 조작 헬퍼 함수들은 이전과 동일)
    def _find_item_by_id(self, data_list, target_id):
        for item in data_list:
            if item.get('id') == target_id: return item
            if item.get('type') == 'L':
                found = self._find_item_by_id(item.get('value', []), target_id)
                if found: return found
        return None

    def _remove_item_by_id(self, data_list, target_id):
        initial_len = len(data_list)
        data_list[:] = [item for item in data_list if item.get('id') != target_id]
        if len(data_list) < initial_len:
            return True
        for item in data_list:
            if item.get('type') == 'L':
                if self._remove_item_by_id(item.get('value', []), target_id):
                    return True
        return False

    def _ensure_ids(self, data_list):
        for item in data_list:
            if 'id' not in item: item['id'] = str(uuid.uuid4())
            if item.get('type') == 'L': self._ensure_ids(item.get('value', []))

    # ... (UI 제어 함수들은 이전과 동일)
    def clear_view(self):
        self._is_internal_update = True
        self.current_item = None
        self.current_manual_message = None
        self.action_type_combo.setEnabled(False)
        self.device_id_combo.setEnabled(False)
        self.delay_spinbox.setEnabled(False)
        self.send_panel.hide()
        self.wait_panel.hide()
        self.send_now_button.hide()
        self.device_id_combo.clear()
        self.delay_spinbox.setValue(0.0)
        self.message_body_tree.clear()
        self.wait_s_spinbox.setValue(0)
        self.wait_f_spinbox.setValue(0)
        self.wait_timeout_spinbox.setValue(10.0)
        self._is_internal_update = False

    @Slot(ScenarioStepItem)
    def display_step_properties(self, item: ScenarioStepItem):
        self._is_internal_update = True
        self.current_item = item
        self.current_manual_message = None
        data = item.step_data
        self.action_type_combo.setEnabled(True)
        self.device_id_combo.setEnabled(True)
        self.delay_spinbox.setEnabled(True)
        is_wait = 'wait_recv' in data
        self.send_now_button.setVisible(not is_wait)
        self.wait_panel.setVisible(is_wait)
        self.send_panel.setVisible(not is_wait)
        self.delay_spinbox.setEnabled(not is_wait)
        self.action_type_combo.setCurrentIndex(1 if is_wait else 0)
        self._populate_common_fields(data)
        if is_wait:
            self.wait_s_spinbox.setValue(data['wait_recv'].get('s', 0))
            self.wait_f_spinbox.setValue(data['wait_recv'].get('f', 0))
            self.wait_timeout_spinbox.setValue(data.get('timeout', 10.0))
            self.message_body_tree.clear()
        else:
            message_body = data.get('message', {}).get('body')
            if message_body is not None:
                self._ensure_ids(message_body)
                self._refresh_ui_from_model(message_body)
            else:
                self.message_body_tree.clear()
        self._is_internal_update = False

    @Slot(dict)
    def display_for_manual_send(self, message_data: dict):
        self._is_internal_update = True
        self.clear_view()
        self.current_manual_message = copy.deepcopy(message_data.get("message"))
        self.action_type_combo.setEnabled(False)
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
        if message_body is not None:
            self._populate_message_tree(self.message_body_tree, message_body)
        self.message_body_tree.expandAll()
        self.message_body_tree.resizeColumnToContents(0)
        self.message_body_tree.resizeColumnToContents(2)
        self._is_internal_update = False

    def _populate_message_tree(self, parent_widget, data_list):
        for item_data in data_list:
            tree_item = QTreeWidgetItem(parent_widget)
            tree_item.setData(0, Qt.ItemDataRole.UserRole, item_data)
            item_type, val = item_data.get('type'), item_data.get('value')
            if item_type == 'L':
                tree_item.setText(0, f"L [{len(val)}]")
                self._populate_message_tree(tree_item, val)
            else:
                tree_item.setText(0, item_type)
                tree_item.setText(1, str(val))
            tree_item.setFlags(tree_item.flags() | Qt.ItemIsEditable)
            self._add_action_buttons(tree_item, item_data)

    def _add_action_buttons(self, tree_item, item_data):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # ✅ 1. 난잡한 UI 개선: 버튼 스타일 변경
        button_style = """
            QPushButton {
                background-color: transparent;
                border: 1px solid #555;
                padding: 1px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #555;
                border: 1px solid #777;
            }
        """

        if item_data.get('type') == 'L':
            add_button = QPushButton("➕")
            add_button.setFixedSize(24, 24)
            add_button.setStyleSheet(button_style)
            add_button.clicked.connect(lambda bound_item=tree_item: self._add_item_action(bound_item))
            layout.addWidget(add_button)

        remove_button = QPushButton("➖")
        remove_button.setFixedSize(24, 24)
        remove_button.setStyleSheet(button_style)
        remove_button.clicked.connect(lambda bound_item=tree_item: self._remove_item_action(bound_item))
        layout.addWidget(remove_button)
        
        layout.addStretch()
        self.message_body_tree.setItemWidget(tree_item, 2, widget)

    # --- 데이터 조작 액션 함수 ---
    @Slot()
    def _add_root_item_action(self):
        self._add_item_action(None)

    # ✅ 2. 하위 리스트 '+' 버튼 오류 해결
    def _add_item_action(self, parent_item: QTreeWidgetItem | None):
        new_item_data = {'id': str(uuid.uuid4()), 'type': 'A', 'value': ''}
        
        # parent_item이 None이면 최상위 리스트에 아이템을 추가
        if parent_item is None:
            target_list = self._get_current_message_body()
            if target_list is not None:
                target_list.append(new_item_data)
        else:
            # parent_item이 있으면, 해당 아이템의 데이터 모델을 찾아서
            # 그 내부의 value 리스트에 아이템을 추가
            root_list = self._get_current_message_body()
            parent_data_model = self._find_item_by_id(root_list, parent_item.data(0, Qt.ItemDataRole.UserRole)['id'])
            if parent_data_model and parent_data_model.get('type') == 'L':
                parent_data_model['value'].append(new_item_data)
        
        self._sync_model_and_views()

    def _remove_item_action(self, item_to_remove: QTreeWidgetItem):
        data = item_to_remove.data(0, Qt.ItemDataRole.UserRole)
        if not data or 'id' not in data: return
        root_list = self._get_current_message_body()
        if root_list is not None:
            if self._remove_item_by_id(root_list, data['id']):
                self._sync_model_and_views()
    
    def _sync_model_and_views(self):
        self._refresh_ui_from_model(self._get_current_message_body())
        if self.current_item: self.current_item.update_visuals()

    # --- 이벤트 핸들러 / 슬롯 (이전과 동일) ---
    @Slot(QTreeWidgetItem, int)
    def on_message_body_item_changed(self, item: QTreeWidgetItem, column: int):
        if self._is_internal_update: return
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not item_data or 'id' not in item_data: return
        root_list = self._get_current_message_body()
        real_data = self._find_item_by_id(root_list, item_data.get('id'))
        if not real_data: return
        if column == 0:
            new_type = item.text(0)
            if new_type != real_data.get('type'):
                real_data['type'] = new_type
                if new_type == 'L': real_data['value'] = []
                elif new_type in ['A', 'B']: real_data['value'] = ''
                elif new_type == 'BOOL': real_data['value'] = False
                else: real_data['value'] = 0
                self._sync_model_and_views()
        elif column == 1:
            new_value_str = item.text(1)
            item_type = real_data.get('type')
            current_value = real_data.get('value')
            try:
                new_value = current_value
                if item_type in ['A', 'B']: new_value = new_value_str
                elif item_type in ['U1', 'U2', 'U4', 'I1', 'I2', 'I4']: new_value = int(new_value_str)
                elif item_type in ['F4', 'F8']: new_value = float(new_value_str)
                elif item_type == 'BOOL': new_value = new_value_str.lower() in ['true', '1', 't', 'y', 'yes']
                if new_value != current_value:
                    real_data['value'] = new_value
                    if self.current_item: self.current_item.update_visuals()
            except (ValueError, TypeError):
                self._is_internal_update = True
                item.setText(1, str(current_value))
                self._is_internal_update = False

    @Slot(int)
    def on_action_type_changed(self, index):
        if self._is_internal_update or not self.current_item: return
        is_wait_action = (index == 1)
        self.wait_panel.setVisible(is_wait_action)
        self.send_panel.setVisible(not is_wait_action)
        self.delay_spinbox.setEnabled(not is_wait_action)
        if is_wait_action:
            original_s = self.current_item.step_data.get('message', {}).get('s', 0)
            original_f = self.current_item.step_data.get('message', {}).get('f', 0)
            self.wait_s_spinbox.setValue(original_s)
            self.wait_f_spinbox.setValue(original_f)
            self.current_item.step_data.pop('message', None)
            self.current_item.step_data.pop('message_id', None)
            self.current_item.step_data['wait_recv'] = {'s': original_s, 'f': original_f}
            self.current_item.step_data['timeout'] = self.wait_timeout_spinbox.value()
        else:
            original_s = self.current_item.step_data.get('wait_recv', {}).get('s', 0)
            original_f = self.current_item.step_data.get('wait_recv', {}).get('f', 0)
            self.current_item.step_data.pop('wait_recv', None)
            self.current_item.step_data.pop('timeout', None)
            self.current_item.step_data['message_id'] = f"Custom S{original_s}F{original_f}"
            self.current_item.step_data['message'] = {'s': original_s, 'f': original_f, 'body': []}
            self._refresh_ui_from_model(self.current_item.step_data['message']['body'])
        self.current_item.update_visuals()

    @Slot()
    def on_wait_condition_changed(self):
        if self._is_internal_update or not self.current_item: return
        if 'wait_recv' in self.current_item.step_data:
            self.current_item.step_data['wait_recv']['s'] = self.wait_s_spinbox.value()
            self.current_item.step_data['wait_recv']['f'] = self.wait_f_spinbox.value()
            self.current_item.step_data['timeout'] = self.wait_timeout_spinbox.value()
            self.current_item.update_visuals()

    @Slot(str)
    def on_device_id_changed(self, text: str):
        if self._is_internal_update: return
        if self.current_item:
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
        message_to_send = None
        if self.current_manual_message:
            message_to_send = self.current_manual_message
        elif self.current_item and 'message' in self.current_item.step_data:
            message_to_send = self.current_item.step_data['message']
        if not device_id or not message_to_send:
            return
        self.manual_send_requested.emit(device_id, message_to_send)