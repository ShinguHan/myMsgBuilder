from PySide6.QtWidgets import QWidget, QHBoxLayout, QSplitter
from PySide6.QtCore import Qt

# 방금 만든 세 개의 위젯 파일을 임포트합니다.
from .message_library_view import MessageLibraryView
from .scenario_timeline_view import ScenarioTimelineView
from .property_editor import PropertyEditor
from .scenario_step_item import ScenarioStepItem

# 필요한 클래스들을 임포트합니다.
from secs_simulator.engine.scenario_manager import ScenarioManager

class ScenarioEditorWidget(QWidget):
    """
    비주얼 시나리오 편집기의 3단 패널을 통합하고 관리하는 메인 위젯입니다.
    """

    # ✅ __init__ 메서드가 scenario_manager와 device_configs를 받도록 수정합니다.
    def __init__(self, scenario_manager: ScenarioManager, device_configs: dict, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # 각 패널에 해당하는 위젯 인스턴스를 생성합니다.
        self.library_view = MessageLibraryView()
        # ✅ 생성할 때 받은 scenario_manager를 ScenarioTimelineView에 전달합니다.
        self.timeline_view = ScenarioTimelineView(scenario_manager)
        # ✅ 생성할 때 받은 device_configs를 PropertyEditor에 전달합니다.
        self.property_editor = PropertyEditor(device_configs)

        # 스플리터에 위젯들을 순서대로 추가합니다.
        splitter.addWidget(self.library_view)
        splitter.addWidget(self.timeline_view)
        splitter.addWidget(self.property_editor)
        
        splitter.setSizes([200, 500, 300])

        # 타임라인 뷰에서 step_selected 시그널이 발생하면,
        # 속성 편집기의 display_step_properties 메소드를 호출하도록 연결합니다.
        self.timeline_view.step_selected.connect(self.property_editor.display_step_properties)
    
    # ✅ 아래 메서드를 클래스에 새로 추가합니다.
    def export_to_scenario_data(self) -> dict:
        """현재 타임라인의 시각적 스텝들을 실행 가능한 JSON 데이터로 변환합니다."""
        steps = []
        # Scene의 아이템들을 y좌표 기준으로 정렬하여 시나리오의 순서를 보장합니다.
        sorted_items = sorted(self.timeline_view.scene.items(), key=lambda item: item.y())
        
        for item in sorted_items:
            if isinstance(item, ScenarioStepItem):
                # UI용 데이터(step_id, device_type 등)는 제외하고
                # Orchestrator 실행에 필요한 데이터만 깔끔하게 추출합니다.
                clean_data = {
                    "device_id": item.step_data.get("device_id"),
                    "delay": item.step_data.get("delay"),
                    "message": item.step_data.get("message")
                }
                steps.append(clean_data)
        
        return {"name": "VisualEditorScenario", "steps": steps}
