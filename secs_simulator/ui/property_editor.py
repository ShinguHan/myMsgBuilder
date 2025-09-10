from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QFormLayout, 
                               QComboBox, QDoubleSpinBox, QTreeWidget, QTreeWidgetItem)
from PySide6.QtCore import Qt

# ScenarioStepItem의 타입을 명시하기 위해 임포트 (실제 순환 참조를 피하기 위한 트릭)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .scenario_step_item import ScenarioStepItem

class PropertyEditor(QWidget):
    def __init__(self, device_configs: dict, parent=None):
        super().__init__(parent)
        self.device_configs = device_configs
        self._is_updating = False 
        self.current_item: 'ScenarioStepItem' | None = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>Step Properties</b>"))
        
        self.form_layout = QFormLayout()
        self.device_id_combo = QComboBox()
        self.delay_spinbox = QDoubleSpinBox()
        self.delay_spinbox.setSuffix(" sec")
        self.delay_spinbox.setSingleStep(0.1)
        self.delay_spinbox.setDecimals(1)
        self.message_body_tree = QTreeWidget()
        self.message_body_tree.setHeaderLabels(["Name", "Value"])

        self.form_layout.addRow("Device ID:", self.device_id_combo)
        self.form_layout.addRow("Delay Before:", self.delay_spinbox)
        layout.addLayout(self.form_layout)
        layout.addWidget(QLabel("<b>Message Body</b>"))
        layout.addWidget(self.message_body_tree)

        # 사용자가 UI 값을 변경하면, _update_step_data 메소드가 호출되도록 연결
        self.device_id_combo.currentTextChanged.connect(self._update_step_data)
        self.delay_spinbox.valueChanged.connect(self._update_step_data)

    def display_step_properties(self, item: 'ScenarioStepItem'):
        """
        타임라인에서 스텝이 선택되면, 해당 스텝의 데이터를 UI에 채웁니다.
        """
        self._is_updating = True # 무한 신호 루프 방지
        self.current_item = item
        data = item.step_data

        # 1. Device ID 콤보박스 설정
        self.device_id_combo.clear()
        device_type = data.get("device_type")
        # 해당 메시지를 보낼 수 있는 장비(같은 타입) 목록만 콤보박스에 추가
        available_devices = [dev_id for dev_id, conf in self.device_configs.items() if conf.get('type') == device_type]
        self.device_id_combo.addItems(available_devices)
        self.device_id_combo.setCurrentText(data.get("device_id"))
        
        # 2. Delay 값 설정
        self.delay_spinbox.setValue(data.get("delay", 0.0))

        # 3. Message Body 트리 뷰 채우기
        self.message_body_tree.clear()
        if "message" in data and "body" in data["message"]:
            self._populate_message_tree(self.message_body_tree, data["message"]["body"])
        
        self.message_body_tree.expandAll()
        self._is_updating = False

    def _populate_message_tree(self, parent_item, data_list):
        """SECS 메시지 바디(리스트)를 재귀적으로 순회하며 트리 위젯을 채웁니다."""
        for item_data in data_list:
            item_type = item_data.get('type')
            item_value = item_data.get('value')
            
            if item_type == 'L':
                tree_item = QTreeWidgetItem(parent_item, [f"L[{len(item_value)}]"])
                self._populate_message_tree(tree_item, item_value) # 재귀 호출
            else:
                # 값(Value) 컬럼을 편집 가능하도록 설정
                tree_item = QTreeWidgetItem(parent_item, [item_type, str(item_value)])
                tree_item.setFlags(tree_item.flags() | Qt.ItemIsEditable)

    def _update_step_data(self):
        """사용자가 UI에서 값을 변경하면, 그 내용이 실제 데이터 모델에 반영됩니다."""
        if self._is_updating or not self.current_item:
            return
            
        # UI 위젯의 현재 값을 읽어와 데이터 모델(딕셔너리)을 업데이트
        self.current_item.step_data['device_id'] = self.device_id_combo.currentText()
        self.current_item.step_data['delay'] = self.delay_spinbox.value()
        
        # 타임라인의 아이템 표시도 업데이트된 내용으로 다시 그리도록 요청
        self.current_item.update()

