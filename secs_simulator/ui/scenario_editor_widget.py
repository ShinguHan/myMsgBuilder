from PySide6.QtWidgets import QWidget, QHBoxLayout, QSplitter
from PySide6.QtCore import Qt

# 방금 만든 세 개의 위젯 파일을 임포트합니다.
from .message_library_view import MessageLibraryView
from .scenario_timeline_view import ScenarioTimelineView
from .property_editor import PropertyEditor

class ScenarioEditorWidget(QWidget):
    """
    비주얼 시나리오 편집기의 3단 패널을 통합하고 관리하는 메인 위젯입니다.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # QSplitter는 사용자가 경계를 드래그하여 각 패널의 크기를 조절할 수 있게 해주는 위젯입니다.
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # 각 패널에 해당하는 위젯 인스턴스를 생성합니다.
        self.library_view = MessageLibraryView()
        self.timeline_view = ScenarioTimelineView()
        self.property_editor = PropertyEditor()

        # 스플리터에 위젯들을 순서대로 추가합니다.
        splitter.addWidget(self.library_view)
        splitter.addWidget(self.timeline_view)
        splitter.addWidget(self.property_editor)
        
        # 초기 패널 너비 비율을 보기 좋게 설정합니다.
        splitter.setSizes([200, 500, 250])
