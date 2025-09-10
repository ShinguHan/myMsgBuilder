from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QFormLayout, 
                               QComboBox, QDoubleSpinBox, QTreeWidget, QTreeWidgetItem)
from PySide6.QtCore import Qt

class PropertyEditor(QWidget):
    """
    선택된 시나리오 스텝의 속성을 표시하고 편집하는 위젯입니다.
    이제 실제 UI 요소들을 갖추게 됩니다.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        # UI 업데이트 중 무한 루프를 방지하기 위한 플래그
        self._is_updating = False 
        # 현재 선택된 타임라인 아이템을 저장할 변수
        self.current_item = None

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<b>Step Properties</b>"))
        
        # 속성을 표시하고 편집할 폼(Form) 레이아웃
        self.form_layout = QFormLayout()
        
        # 1. Device ID를 선택할 콤보박스
        self.device_id_combo = QComboBox()
        
        # 2. Delay 시간을 조절할 스핀박스
        self.delay_spinbox = QDoubleSpinBox()
        self.delay_spinbox.setSuffix(" sec")
        self.delay_spinbox.setSingleStep(0.1)
        self.delay_spinbox.setDecimals(1)
        
        # 3. 메시지 Body 구조를 보여줄 트리 위젯
        self.message_body_tree = QTreeWidget()
        self.message_body_tree.setHeaderLabels(["Name", "Value"])

        # 폼 레이아웃에 위젯들을 추가
        self.form_layout.addRow("Device ID:", self.device_id_combo)
        self.form_layout.addRow("Delay Before:", self.delay_spinbox)
        
        layout.addLayout(self.form_layout)
        layout.addWidget(QLabel("<b>Message Body</b>"))
        layout.addWidget(self.message_body_tree)

    def display_step_properties(self, item):
        """
        타임라인에서 스텝이 선택되면 이 메소드가 호출되어
        해당 스텝의 데이터를 UI에 표시합니다. (8장에서 구체적으로 구현)
        """
        self._is_updating = True
        self.current_item = item
        # TODO: item의 데이터를 가져와 각 위젯(콤보박스, 스핀박스 등)에 채우는 로직 추가
        print(f"DEBUG: Displaying properties for item.")
        self._is_updating = False

    def _update_step_data(self):
        """
        사용자가 UI 값을 변경하면, 그 내용이 실제 데이터에 반영됩니다.
        (8장에서 구체적으로 구현)
        """
        if self._is_updating or not self.current_item:
            return
        # TODO: 각 위젯의 현재 값을 읽어 self.current_item의 데이터에 업데이트하는 로직 추가
        print(f"DEBUG: Step data updated.")

