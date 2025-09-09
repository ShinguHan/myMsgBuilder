from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

class PropertyEditor(QWidget):
    """선택된 시나리오 스텝의 속성을 편집하는 위젯 (현재는 Placeholder)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        label = QLabel("<b>Step Properties</b><br><br>Select a step in the timeline to edit its properties.")
        label.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(label)
        layout.addStretch()
