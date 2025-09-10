# secs_simulator/ui/scenario_editor/property_editor.py

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QFormLayout, QGraphicsItem,
                               QComboBox, QDoubleSpinBox, QTreeWidget, QTreeWidgetItem)
from PySide6.QtCore import Qt, Slot

from .scenario_step_item import ScenarioStepItem

class PropertyEditor(QWidget):
    """선택된 시나리오 스텝의 속성을 표시하고 편집하는 위젯입니다."""

    def __init__(self, device_configs: dict, parent=None):
        super().__init__(parent)
        self.device_configs = device_configs
        self.current_item: ScenarioStepItem | None = None
        self._is_internal_update = False # 내부 코드에 의한 업데이트인지 사용자에 의한 것인지 구분하는 플래그

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

        # --- 신호(Signal)와 슬롯(Slot) 연결 ---
        self.device_id_combo.currentTextChanged.connect(self.on_ui_changed)
        self.delay_spinbox.valueChanged.connect(self.on_ui_changed)
        self.message_body_tree.itemChanged.connect(self.on_tree_item_changed)

    @Slot(QGraphicsItem)
    def display_step_properties(self, item: ScenarioStepItem):
        """타임라인에서 스텝이 선택되면 이 슬롯이 호출되어 속성을 표시합니다."""
        self._is_internal_update = True  # 코드에 의한 UI 변경 시작
        self.current_item = item
        data = item.step_data

        # 1. Device ID 콤보박스 설정
        self.device_id_combo.clear()
        device_type = data.get("device_type")
        available_devices = [dev_id for dev_id, conf in self.device_configs.items() if conf.get('type') == device_type]
        self.device_id_combo.addItems(available_devices)
        self.device_id_combo.setCurrentText(data.get("device_id", "Select Device..."))
        
        # 2. Delay 값 설정
        self.delay_spinbox.setValue(data.get("delay", 0))

        # 3. Message Body 트리 뷰 채우기
        self.message_body_tree.clear()
        if "message" in data and "body" in data["message"]:
            self._populate_message_tree(self.message_body_tree, data["message"]["body"])
        
        self.message_body_tree.expandAll()
        self.message_body_tree.resizeColumnToContents(0)
        self._is_internal_update = False # 코드에 의한 UI 변경 끝

    def _populate_message_tree(self, parent_widget, data_list: list):
        for item_data in data_list:
            item_type, item_value = item_data.get('type'), item_data.get('value')
            tree_item = QTreeWidgetItem(parent_widget, [item_type, str(item_value)])
            tree_item.setData(0, Qt.ItemDataRole.UserRole, item_data) # 원본 데이터 참조 저장
            
            if item_type == 'L':
                tree_item.setText(0, f"L[{len(item_value)}]")
                self._populate_message_tree(tree_item, item_value) # 재귀
            else:
                tree_item.setFlags(tree_item.flags() | Qt.ItemIsEditable)

    @Slot()
    def on_ui_changed(self, *args):
        """Device ID, Delay 등 UI 값이 사용자에 의해 변경됐을 때 호출됩니다."""
        if self._is_internal_update or not self.current_item:
            return
            
        # 1. 현재 UI의 값을 가져와 데이터 모델(step_data)에 반영합니다.
        self.current_item.step_data['device_id'] = self.device_id_combo.currentText()
        self.current_item.step_data['delay'] = self.delay_spinbox.value()
        
        # 2. 데이터가 바뀌었으니, 타임라인 아이템을 새로 그리라고 명령합니다.
        self.current_item.update()

    @Slot(QTreeWidgetItem, int)
    def on_tree_item_changed(self, item: QTreeWidgetItem, column: int):
        """Message Body 트리에서 값이 수정되었을 때 호출됩니다."""
        if self._is_internal_update or column != 1:
            return

        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not item_data: return

        new_value_str = item.text(1)
        item_type = item_data.get('type')
        
        # 값 유효성 검사 및 변환
        try:
            if item_type in ['A', 'B']: new_value = new_value_str
            elif 'I' in item_type or 'U' in item_type: new_value = int(new_value_str)
            elif 'F' in item_type: new_value = float(new_value_str)
            else: new_value = new_value_str
            
            # 원본 데이터 모델의 값을 직접 수정
            item_data['value'] = new_value
        except (ValueError, TypeError):
            # 변환 실패 시 원래 값으로 되돌림
            self._is_internal_update = True
            item.setText(1, str(item_data.get('value')))
            self._is_internal_update = False