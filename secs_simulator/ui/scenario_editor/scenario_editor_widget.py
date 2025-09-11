from PySide6.QtWidgets import QWidget, QHBoxLayout, QSplitter
from PySide6.QtCore import Qt, Signal

from .message_library_view import MessageLibraryView
from .scenario_timeline_view import ScenarioTimelineView
from .property_editor import PropertyEditor
from .scenario_step_item import ScenarioStepItem
from secs_simulator.engine.scenario_manager import ScenarioManager

class ScenarioEditorWidget(QWidget):
    """
    비주얼 시나리오 편집기의 3단 패널을 통합하고 관리하는 메인 위젯입니다.
    """
    manual_send_requested = Signal(str, dict)

    def __init__(self, scenario_manager: ScenarioManager, device_configs: dict, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        self.library_view = MessageLibraryView()
        self.timeline_view = ScenarioTimelineView(scenario_manager)
        self.property_editor = PropertyEditor(device_configs, scenario_manager)

        splitter.addWidget(self.library_view)
        splitter.addWidget(self.timeline_view)
        splitter.addWidget(self.property_editor)
        
        splitter.setSizes([250, 600, 350])

        # --- 시그널-슬롯 연결 ---
        self.timeline_view.step_selected.connect(self.property_editor.display_step_properties)
        self.library_view.message_selected.connect(self.property_editor.display_for_manual_send)
        self.property_editor.manual_send_requested.connect(self.manual_send_requested)
    
    def export_to_scenario_data(self) -> dict:
        """현재 타임라인을 실행 가능한 JSON 데이터로 변환합니다."""
        steps = []
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

    def export_to_master_scenario(self) -> dict:
        """현재 타임라인을 저장 가능한 master_scenario 형식으로 변환합니다."""
        steps = []
        sorted_items = sorted(self.timeline_view.scene.items(), key=lambda item: item.y())
        
        for item in sorted_items:
            if isinstance(item, ScenarioStepItem):
                step_data = {
                    "device_id": item.step_data.get("device_id"),
                    "delay": item.step_data.get("delay"),
                    "message_id": item.step_data.get("message_id")
                }
                steps.append(step_data)
        
        return {"name": "VisualEditorScenario", "steps": steps}

    def load_from_scenario_data(self, scenario_data: dict):
        """로드된 시나리오 데이터로 타임라인을 재구성합니다."""
        self.timeline_view.scene.clear()
        self.timeline_view.y_pos_counter = 10
        self.property_editor.clear_view()

        manager = self.timeline_view.scenario_manager
        for step_data in scenario_data.get("steps", []):
            device_id = step_data.get("device_id")
            message_id = step_data.get("message_id")
            if not all([device_id, message_id]): continue

            device_type = manager.get_device_type(device_id)
            if not device_type: continue

            message_body = manager.get_message_body(device_type, message_id)
            if not message_body: continue
            
            full_step_data = {**step_data, "message": message_body, "device_type": device_type}

            item = ScenarioStepItem(full_step_data)
            item.signals.selected.connect(self.timeline_view.step_selected)
            self.timeline_view.scene.addItem(item)
            item.setPos(10, self.timeline_view.y_pos_counter)
            self.timeline_view.y_pos_counter += item.boundingRect().height() + 10

