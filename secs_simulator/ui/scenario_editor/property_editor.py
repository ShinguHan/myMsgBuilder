# secs_simulator/ui/scenario_editor/property_editor.py

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QFormLayout, 
                               QComboBox, QDoubleSpinBox, QTreeWidget, QTreeWidgetItem)
from PySide6.QtCore import Slot, Qt

from .scenario_step_item import ScenarioStepItem
from secs_simulator.engine.scenario_manager import ScenarioManager

class PropertyEditor(QWidget):
    """모든 속성을 편집하고 실시간으로 모델에 반영하는 최종 편집기입니다."""

    def __init__(self, device_configs: dict, scenario_manager: ScenarioManager, parent=None):
        super().__init__(parent)
        self.device_configs = device_configs
        self.scenario_manager = scenario_manager
        self.current_item: ScenarioStepItem | None = None
        self._is_internal_update = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.addWidget(QLabel("<b>Step Properties</b>"))
        
        self.form_layout = QFormLayout()
        self.device_id_combo = QComboBox()
        self.message_id_combo = QComboBox()
        self.delay_spinbox = QDoubleSpinBox()
        self.delay_spinbox.setSuffix(" sec")
        self.delay_spinbox.setDecimals(1)
        
        self.message_body_tree = QTreeWidget()
        self.message_body_tree.setHeaderLabels(["Name", "Value"])

        self.form_layout.addRow("Device ID:", self.device_id_combo)
        self.form_layout.addRow("Message ID:", self.message_id_combo)
        self.form_layout.addRow("Delay Before:", self.delay_spinbox)
        layout.addLayout(self.form_layout)
        layout.addWidget(QLabel("<b>Message Body</b>"))
        layout.addWidget(self.message_body_tree)

        self.device_id_combo.currentTextChanged.connect(self.on_device_id_changed)
        self.message_id_combo.currentTextChanged.connect(self.on_message_id_changed)
        self.delay_spinbox.valueChanged.connect(self.on_delay_changed)
        self.message_body_tree.itemChanged.connect(self.on_body_changed)

    @Slot(ScenarioStepItem)
    def display_step_properties(self, item: ScenarioStepItem):
        self._is_internal_update = True
        self.current_item = item
        data = item.step_data
        device_type = data.get("device_type")

        # --- Device ID 설정 ---
        self.device_id_combo.clear()
        available_devices = [dev_id for dev_id, conf in self.device_configs.items() if conf.get('type') == device_type]
        self.device_id_combo.addItems(available_devices)
        self.device_id_combo.setCurrentText(data.get("device_id"))
        
        # --- Message ID 목록 설정 ---
        self.message_id_combo.clear()
        if device_type:
            library = self.scenario_manager._load_message_library(device_type)
            if library: self.message_id_combo.addItems(library.keys())
        self.message_id_combo.setCurrentText(data.get("message_id"))
        
        # --- Delay 설정 ---
        self.delay_spinbox.setValue(data.get("delay", 0))

        # ✅ [비밀 해결] UI에 표시된 초기값을 데이터 모델에 즉시 강제로 동기화합니다.
        # 이렇게 하면 사용자가 값을 바꾸지 않아도 (항목이 1개일 때 등) 데이터가 정확히 저장됩니다.
        initial_device_id = self.device_id_combo.currentText()
        if data['device_id'] != initial_device_id:
            data['device_id'] = initial_device_id
            self.current_item.update() # 타임라인 아이템 즉시 갱신

        # --- Message Body 설정 ---
        self.message_body_tree.clear()
        if "message" in data and "body" in data["message"]:
            self._populate_message_tree(self.message_body_tree, data["message"]["body"])
        self.message_body_tree.expandAll()
        
        self._is_internal_update = False

    def _populate_message_tree(self, parent_widget, data_list):
        for item_data in data_list:
            item_type, val = item_data.get('type'), item_data.get('value')
            tree_item = QTreeWidgetItem(parent_widget, [item_type, str(val)])
            tree_item.setData(0, Qt.ItemDataRole.UserRole, item_data)
            if item_type == 'L':
                tree_item.setText(0, f"L[{len(val)}]")
                self._populate_message_tree(tree_item, val)
            else:
                tree_item.setFlags(tree_item.flags() | Qt.ItemIsEditable)

    # --- 각 UI 요소 변경에 대한 개별 슬롯 (이전과 동일) ---
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

    @Slot(str)
    def on_message_id_changed(self, text: str):
        if self._is_internal_update or not self.current_item or not text: return
        
        self.current_item.step_data['message_id'] = text
        device_type = self.current_item.step_data.get("device_type")
        new_message_body = self.scenario_manager.get_message_body(device_type, text)
        
        if new_message_body:
            self.current_item.step_data['message'] = new_message_body
            self.display_step_properties(self.current_item)
        
        self.current_item.update()

    @Slot(QTreeWidgetItem, int)
    def on_body_changed(self, item: QTreeWidgetItem, column: int):
        if self._is_internal_update or not self.current_item or column != 1: return

        def parse_tree(parent_item):
            result = []
            for i in range(parent_item.childCount()):
                child = parent_item.child(i)
                type_name, value_text = child.text(0), child.text(1)
                try:
                    if 'I' in type_name or 'U' in type_name: value = int(value_text)
                    elif 'F' in type_name: value = float(value_text)
                    else: value = value_text
                except ValueError: value = value_text

                if type_name.startswith("L["):
                    result.append({"type": "L", "value": parse_tree(child)})
                else:
                    result.append({"type": type_name, "value": value})
            return result

        new_body = parse_tree(self.message_body_tree.invisibleRootItem())
        self.current_item.step_data["message"]["body"] = new_body
        self.current_item.update()