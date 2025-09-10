# secs_simulator/ui/scenario_editor/scenario_editor_widget.py

from PySide6.QtWidgets import QWidget, QHBoxLayout, QSplitter
from PySide6.QtCore import Qt

from .message_library_view import MessageLibraryView
from .scenario_timeline_view import ScenarioTimelineView
from .property_editor import PropertyEditor
from secs_simulator.engine.scenario_manager import ScenarioManager
from .scenario_step_item import ScenarioStepItem

class ScenarioEditorWidget(QWidget):
    """
    비주얼 시나리오 편집기의 3단 패널을 통합하고 관리하는 메인 위젯입니다.
    """

    def __init__(self, scenario_manager: ScenarioManager, device_configs: dict, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        self.library_view = MessageLibraryView()
        self.timeline_view = ScenarioTimelineView(scenario_manager)
        self.property_editor = PropertyEditor(device_configs)

        splitter.addWidget(self.library_view)
        splitter.addWidget(self.timeline_view)
        splitter.addWidget(self.property_editor)
        
        splitter.setSizes([200, 500, 300])

        # ✅ [핵심 연결] 타임라인에서 스텝이 선택되면(step_selected 신호),
        # 속성 편집기의 display_step_properties 슬롯을 호출하도록 연결합니다.
        self.timeline_view.step_selected.connect(self.property_editor.display_step_properties)
    
    def export_to_scenario_data(self) -> dict:
        """현재 타임라인의 시각적 스텝들을 실행 가능한 JSON 데이터로 변환합니다."""
        steps = []
        # Scene의 아이템들을 y좌표 기준으로 정렬하여 시나리오의 순서를 보장합니다.
        sorted_items = sorted(self.timeline_view.scene.items(), key=lambda item: item.y())
        
        for item in sorted_items:
            if isinstance(item, ScenarioStepItem):
                clean_data = {
                    "device_id": item.step_data.get("device_id"),
                    "delay": item.step_data.get("delay"),
                    "message": item.step_data.get("message")
                }
                steps.append(clean_data)
        
        return {"name": "VisualEditorScenario", "steps": steps}