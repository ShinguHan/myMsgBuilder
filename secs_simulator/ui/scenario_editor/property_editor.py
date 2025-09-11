from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QFormLayout, 
                               QComboBox, QDoubleSpinBox, QTreeWidget, QTreeWidgetItem,
                               QPushButton)
from PySide6.QtCore import Slot, Qt, Signal

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

        self.device_id_combo.currentTextChanged.connect(self.on_device_id_changed)
        self.delay_spinbox.valueChanged.connect(self.on_delay_changed)
        self.send_now_button.clicked.connect(self.on_send_now_clicked)
        # ✅ [핵심 기능] Tree 아이템의 값이 변경되었을 때 호출될 슬롯 연결
        self.message_body_tree.itemChanged.connect(self.on_message_body_item_changed)
        
        self.clear_view()

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

        device_type = data.get("device_type")
        self.device_id_combo.clear()
        available_devices = [dev_id for dev_id, conf in self.device_configs.items() if conf.get('type') == device_type]
        self.device_id_combo.addItems(available_devices)
        self.device_id_combo.setCurrentText(data.get("device_id"))
        
        self.delay_spinbox.setValue(data.get("delay", 0))

        initial_device_id = self.device_id_combo.currentText()
        if data['device_id'] != initial_device_id:
            data['device_id'] = initial_device_id
            self.current_item.update()

        self.message_body_tree.clear()
        if "message" in data and "body" in data["message"]:
            self._populate_message_tree(self.message_body_tree, data["message"]["body"])
        self.message_body_tree.expandAll()
        self._is_internal_update = False

    @Slot(dict)
    def display_for_manual_send(self, message_data: dict):
        """수동 메시지 전송 모드로 UI를 설정합니다."""
        self._is_internal_update = True
        self.current_item = None
        self.current_manual_message = message_data.get("message")

        self.form_layout.labelForField(self.delay_spinbox).hide()
        self.delay_spinbox.hide()
        self.send_now_button.show()

        device_type = message_data.get("device_type")
        self.device_id_combo.clear()
        available_devices = [dev_id for dev_id, conf in self.device_configs.items() if conf.get('type') == device_type]
        self.device_id_combo.addItems(available_devices)

        self.message_body_tree.clear()
        if "body" in self.current_manual_message:
             self._populate_message_tree(self.message_body_tree, self.current_manual_message["body"])
        self.message_body_tree.expandAll()
        self._is_internal_update = False

    def _populate_message_tree(self, parent_widget, data_list):
        """데이터 모델을 기반으로 Tree 위젯을 재귀적으로 생성합니다."""
        for item_data in data_list:
            item_type, val = item_data.get('type'), item_data.get('value')
            tree_item = QTreeWidgetItem(parent_widget)
            
            # ✅ [핵심 기능] 각 Tree 아이템에 실제 데이터(dict)를 저장합니다.
            tree_item.setData(0, Qt.ItemDataRole.UserRole, item_data)

            if item_type == 'L':
                tree_item.setText(0, f"L[{len(val)}]")
                self._populate_message_tree(tree_item, val)
            else:
                tree_item.setText(0, item_type)
                tree_item.setText(1, str(val))
                # ✅ L 타입이 아닌 경우에만 값(Value) 컬럼을 편집 가능하도록 설정
                tree_item.setFlags(tree_item.flags() | Qt.ItemIsEditable)

    @Slot(QTreeWidgetItem, int)
    def on_message_body_item_changed(self, item: QTreeWidgetItem, column: int):
        """사용자가 Tree의 값을 수정했을 때 데이터 모델을 업데이트합니다."""
        if self._is_internal_update or column != 1:
            return

        item_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not item_data:
            return

        new_value_str = item.text(1)
        item_type = item_data.get('type')
        current_value = item_data.get('value')
        
        new_value = current_value
        try:
            # ✅ [핵심 기능] 타입에 맞게 값 유효성 검사 및 변환
            if item_type in ['A', 'B']:
                new_value = new_value_str
            elif item_type in ['U1', 'U2', 'U4', 'I1', 'I2', 'I4']:
                new_value = int(new_value_str)
            elif item_type in ['F4', 'F8']:
                new_value = float(new_value_str)
            elif item_type == 'BOOL':
                # 'true', '1', 'yes' 등을 True로 인식하도록 처리
                new_value = new_value_str.lower() in ['true', '1', 't', 'y', 'yes']

            # ✅ [핵심 기능] 변환 성공 시, 실제 데이터 모델(dict)의 값을 업데이트
            item_data['value'] = new_value
            
            # ScenarioStepItem의 step_data도 업데이트하여 변경사항을 최종 반영
            if self.current_item:
                 self.current_item.update()

        except (ValueError, TypeError):
            # ✅ [핵심 기능] 변환 실패 시, UI의 값을 이전 값으로 되돌려 데이터 무결성 유지
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
        device_id = self.device_id_combo.currentText()
        if not device_id or not self.current_manual_message:
            return
        # TODO: 수동 전송 시에도 편집된 메시지 Body가 전송되도록 개선 필요
        self.manual_send_requested.emit(device_id, self.current_manual_message)