from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QFormLayout, 
                               QComboBox, QDoubleSpinBox, QTreeWidget, QTreeWidgetItem)
from PySide6.QtCore import Qt

from .scenario_step_item import ScenarioStepItem

class PropertyEditor(QWidget):
    """선택된 시나리오 스텝의 속성을 표시하고 편집하는 위젯입니다."""

    def __init__(self, device_configs: dict, parent=None):
        super().__init__(parent)
        self.device_configs = device_configs
        self.current_item: ScenarioStepItem | None = None
        self._is_updating = False # 신호가 무한 반복되는 것을 방지하는 플래그

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        layout.addWidget(QLabel("<b>Step Properties</b>"))
        
        self.form_layout = QFormLayout()
        self.device_id_combo = QComboBox()
        self.delay_spinbox = QDoubleSpinBox()
        self.delay_spinbox.setSuffix(" sec")
        self.delay_spinbox.setDecimals(1)
        self.delay_spinbox.setSingleStep(0.1)
        
        self.message_body_tree = QTreeWidget()
        self.message_body_tree.setHeaderLabels(["Name", "Value"])

        self.form_layout.addRow("Device ID:", self.device_id_combo)
        self.form_layout.addRow("Delay Before:", self.delay_spinbox)
        layout.addLayout(self.form_layout)
        layout.addWidget(QLabel("<b>Message Body</b>"))
        layout.addWidget(self.message_body_tree)

        # ✅ 1. UI 값이 변경되었다는 '신호(Signal)'를 받았을 때
        #    _update_step_data 라는 '슬롯(Slot)' 함수를 실행하도록 연결합니다.
        self.device_id_combo.currentTextChanged.connect(self._update_step_data)
        self.delay_spinbox.valueChanged.connect(self._update_step_data)

    def display_step_properties(self, item: ScenarioStepItem):
        """타임라인에서 스텝이 선택되면 이 함수가 호출되어 속성을 표시합니다."""
        self._is_updating = True # 값을 설정하는 동안에는 _update_step_data가 호출되지 않도록 방지
        self.current_item = item
        data = item.step_data

        # Device ID 콤보박스 설정
        self.device_id_combo.clear()
        device_type = data.get("device_type")
        available_devices = [dev_id for dev_id, conf in self.device_configs.items() if conf.get('type') == device_type]
        self.device_id_combo.addItems(available_devices)
        self.device_id_combo.setCurrentText(data.get("device_id"))
        
        # Delay 값 설정
        self.delay_spinbox.setValue(data.get("delay", 0))

        # Message Body 트리 뷰 채우기
        self.message_body_tree.clear()
        if "message" in data and "body" in data["message"]:
            self._populate_message_tree(self.message_body_tree, data["message"]["body"])
        
        self.message_body_tree.expandAll()
        self._is_updating = False # 설정이 끝났으므로 다시 신호를 받을 수 있도록 허용

    def _populate_message_tree(self, parent_item, data_list):
        """SECS 메시지 바디(리스트)를 재귀적으로 순회하며 트리 위젯을 채웁니다."""
        for i, item_data in enumerate(data_list):
            if isinstance(item_data, dict) and 'type' in item_data:
                item_type = item_data.get('type')
                item_value = item_data.get('value')
                
                if item_type == 'L':
                    tree_item = QTreeWidgetItem(parent_item, [f"L[{len(item_value)}]"])
                    self._populate_message_tree(tree_item, item_value) # 재귀 호출
                else:
                    QTreeWidgetItem(parent_item, [item_type, str(item_value)])

    def _update_step_data(self):
        """✅ 2. UI에서 값이 변경되면, 선택된 아이템의 데이터 모델을 업데이트합니다."""
        if self._is_updating or not self.current_item:
            return
            
        # 3. 현재 UI의 값을 가져와서 선택된 아이템의 데이터(step_data)에 덮어씁니다.
        self.current_item.step_data['device_id'] = self.device_id_combo.currentText()
        self.current_item.step_data['delay'] = self.delay_spinbox.value()
        
        # 4. 데이터가 바뀌었으니, 타임라인의 아이템을 새로 그리라고 명령합니다.
        self.current_item.update()

