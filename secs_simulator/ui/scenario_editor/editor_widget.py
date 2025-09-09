from PySide6.QtWidgets import QWidget, QHBoxLayout, QSplitter
from PySide6.QtCore import Qt

from .message_library_view import MessageLibraryView
from .scenario_timeline_view import ScenarioTimelineView
from .property_editor import PropertyEditor

class ScenarioEditorWidget(QWidget):
    """비주얼 시나리오 편집기의 3단 패널을 통합하는 메인 위젯입니다."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        self.library_view = MessageLibraryView()
        self.timeline_view = ScenarioTimelineView()
        self.property_editor = PropertyEditor()

        splitter.addWidget(self.library_view)
        splitter.addWidget(self.timeline_view)
        splitter.addWidget(self.property_editor)
        
        # 각 패널의 너비 비율 설정
        splitter.setSizes([200, 500, 250])
