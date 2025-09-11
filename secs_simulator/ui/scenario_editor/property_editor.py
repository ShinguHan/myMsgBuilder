from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QFormLayout, 
                               QComboBox, QDoubleSpinBox, QTreeWidget, QTreeWidgetItem,
                               QPushButton, QMenu, QInputDialog, QMessageBox)
from PySide6.QtCore import Slot, Qt, Signal
from PySide6.QtGui import QAction

from .scenario_step_item import ScenarioStepItem
from secs_simulator.engine.scenario_manager import ScenarioManager
import copy

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

        # ✅ [기능 추가] 우클릭 컨텍스트 메뉴를 위한 설정
        self.message_body_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.message_body_tree.customContextMenuRequested.connect(self._show_context_menu)
        
        self.clear_view()

    # --- UI Mode Control ---
    def clear_view(self):
        """뷰를 초기 상태로 리셋합니다."""
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
        """타임라인 스텝 편집 모드로 UI를 설정합니다."""
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
        """수동 메시지 전송 모드로 UI를 설정합니다."""
        self._is_internal_update = True
        self.current_item = None
        # ✅ 수동 전송 시 원본 라이브러리 메시지가 수정되지 않도록 깊은 복사 사용
        self.current_manual_message = copy.deepcopy(message_data.get("message"))
        self.form_layout.labelForField(self.delay_spinbox).hide()
        self.delay_spinbox.hide()
        self.send_now_button.show()
        self._populate_common_fields(message_data)
        self._is_internal_update = False
    
    def _populate_common_fields(self, data_source: dict):
        """두 모드에서 공통적으로 사용되는 UI 필드를 채웁니다."""
        device_type = data_source.get("device_type")
        self.device_id_combo.clear()
        available_devices = [dev_id for dev_id, conf in self.device_configs.items() if conf.get('type') == device_type]
        self.device_id_combo.addItems(available_devices)
        if isinstance(data_source, dict) and data_source.get("device_id"):
             self.device_id_combo.setCurrentText(data_source.get("device_id"))
        
        self.delay_spinbox.setValue(data_source.get("delay", 0))

        message_body = self._get_current_message_body()
        self._refresh_ui_from_model(message_body)
    
    # --- Data Model & UI Synchronization ---
    def _get_current_message_body(self) -> list | None:
        """현재 편집 대상(스텝 또는 수동 메시지)의 body 리스트를 반환합니다."""
        if self.current_item:
            return self.current_item.step_data.get("message", {}).get("body")
        if self.current_manual_message:
            return self.current_manual_message.get("body")
        return None

    def _refresh_ui_from_model(self, message_body: list | None):
        """주어진 데이터 모델을 기반으로 Tree View 전체를 다시 그립니다."""
        self._is_internal_update = True
        self.message_body_tree.clear()
        if message_body is not None:
            self._populate_message_tree(self.message_body_tree, message_body)
        self.message_body_tree.expandAll()
        self._is_internal_update = False

    def _populate_message_tree(self, parent_widget, data_list):
        """데이터 모델을 기반으로 Tree 위젯을 재귀적으로 생성합니다."""
        for item_data in data_list:
            item_type, val = item_data.get('type'), item_data.get('value')
            tree_item = QTreeWidgetItem(parent_widget)
            tree_item.setData(0, Qt.ItemDataRole.UserRole, item_data)
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
        """Tree 위젯에서 우클릭 시 컨텍스트 메뉴를 표시합니다."""
        selected_item = self.message_body_tree.currentItem()
        if not selected_item: return

        menu = QMenu()
        # 'L' 타입이거나, 부모가 'L' 타입인 경우에만 아이템 추가/삭제 가능
        can_add = selected_item.data(0, Qt.ItemDataRole.UserRole).get('type') == 'L'
        can_remove = selected_item.parent() is not None

        if can_add:
            add_action = menu.addAction("Add New Item")
            add_action.triggered.connect(lambda: self._add_item_action(selected_item))
        
        if can_remove:
            remove_action = menu.addAction("Remove Selected Item")
            remove_action.triggered.connect(lambda: self._remove_item_action(selected_item))
        
        change_type_action = menu.addAction("Change Type")
        change_type_action.triggered.connect(lambda: self._change_type_action(selected_item))
        
        menu.exec(self.message_body_tree.mapToGlobal(position))

    def _add_item_action(self, selected_item: QTreeWidgetItem):
        """'아이템 추가' 액션을 처리합니다."""
        item_data = selected_item.data(0, Qt.ItemDataRole.UserRole)
        if item_data.get('type') != 'L': return

        SECS_TYPES = ['L', 'A', 'B', 'U1', 'U2', 'U4', 'I1', 'I2', 'I4', 'F4', 'F8', 'BOOL']
        item_type, ok = QInputDialog.getItem(self, "Add SECS Item", "Select item type:", SECS_TYPES, 0, False)
        if not ok: return

        new_item_data = {'type': item_type, 'value': [] if item_type == 'L' else 0 if item_type != 'A' else ''}
        item_data['value'].append(new_item_data)
        
        self._refresh_ui_from_model(self._get_current_message_body())
        if self.current_item: self.current_item.update()

    def _remove_item_action(self, selected_item: QTreeWidgetItem):
        """'아이템 삭제' 액션을 처리합니다."""
        parent_item = selected_item.parent()
        if not parent_item:
            QMessageBox.warning(self, "Action Denied", "Cannot remove the root message body.")
            return

        reply = QMessageBox.question(self, "Confirm Removal",
                                     f"Are you sure you want to remove this item?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                     QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No: return

        parent_data = parent_item.data(0, Qt.ItemDataRole.UserRole)
        selected_data = selected_item.data(0, Qt.ItemDataRole.UserRole)
        
        if parent_data and parent_data.get('type') == 'L' and selected_data in parent_data.get('value', []):
            parent_data['value'].remove(selected_data)
            self._refresh_ui_from_model(self._get_current_message_body())
            if self.current_item: self.current_item.update()

    def _change_type_action(self, selected_item: QTreeWidgetItem):
        """'타입 변경' 액션을 처리합니다."""
        item_data = selected_item.data(0, Qt.ItemDataRole.UserRole)
        if not item_data: return

        SECS_TYPES = ['L', 'A', 'B', 'U1', 'U2', 'U4', 'I1', 'I2', 'I4', 'F4', 'F8', 'BOOL']
        new_type, ok = QInputDialog.getItem(self, "Change Item Type", "Select new type:", SECS_TYPES, 0, False)
        if not ok or new_type == item_data.get('type'): return

        item_data['type'] = new_type
        item_data['value'] = [] if new_type == 'L' else 0 if new_type not in ['A','B'] else ''
        
        self._refresh_ui_from_model(self._get_current_message_body())
        if self.current_item: self.current_item.update()

    # --- Event Handlers / Slots ---
    @Slot(QTreeWidgetItem, int)
    def on_message_body_item_changed(self, item: QTreeWidgetItem, column: int):
        """사용자가 Tree의 값을 수정했을 때 데이터 모델을 업데이트합니다."""
        if self._is_internal_update or column != 1: return
        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not item_data: return

        new_value_str, item_type = item.text(1), item_data.get('type')
        current_value, new_value = item_data.get('value'), item_data.get('value')
        try:
            if item_type in ['A', 'B']: new_value = new_value_str
            elif item_type in ['U1', 'U2', 'U4', 'I1', 'I2', 'I4']: new_value = int(new_value_str)
            elif item_type in ['F4', 'F8']: new_value = float(new_value_str)
            elif item_type == 'BOOL': new_value = new_value_str.lower() in ['true', '1', 't', 'y', 'yes']
            
            item_data['value'] = new_value
            if self.current_item: self.current_item.update()
        except (ValueError, TypeError):
            self._is_internal_update = True
            item.setText(1, str(current_value))
            self._is_internal_update = False

    @Slot(str)
    def on_device_id_changed(self, text: str):
        if self._is_internal_update or not self.current_item: return
        self.current_item.step_data['device_id'] = text
        self.current_item.update()

    @Slot(float)
    def on_delay_changed(self, value: float):
        if self._is_internal_update or not self.current_item: return
        self.current_item.step_data['delay'] = value
        self.current_item.update()

    @Slot()
    def on_send_now_clicked(self):
        """수동 전송 버튼 클릭 시 편집된 메시지 내용을 전송합니다."""
        device_id = self.device_id_combo.currentText()
        if not device_id or not self.current_manual_message:
            return
        self.manual_send_requested.emit(device_id, self.current_manual_message)
