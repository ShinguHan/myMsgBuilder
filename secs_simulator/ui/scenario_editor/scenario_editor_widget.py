# secs_simulator/ui/scenario_editor/scenario_editor_widget.py

from PySide6.QtWidgets import QWidget, QHBoxLayout, QSplitter
from PySide6.QtCore import Qt, Signal
import copy

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
        self.timeline_view.step_deleted.connect(self.property_editor.clear_view)
        self.library_view.message_selected.connect(self.property_editor.display_for_manual_send)
        self.property_editor.manual_send_requested.connect(self.manual_send_requested)
    
    def export_to_scenario_data(self) -> dict:
        """✅ [핵심 수정] 현재 타임라인을 실행 가능한 JSON 데이터로 변환합니다."""
        steps = []
        # QGraphicsScene.items()는 정렬 순서를 보장하지 않으므로 y좌표로 정렬합니다.
        sorted_items = sorted(
            [item for item in self.timeline_view.scene.items() if isinstance(item, ScenarioStepItem)],
            key=lambda item: item.y()
        )
        
        for item in sorted_items:
            # 'wait_recv'를 포함한 모든 데이터를 그대로 복사하여 전달합니다.
            # 이렇게 해야 Orchestrator가 'wait' 액션을 인지할 수 있습니다.
            steps.append(copy.deepcopy(item.step_data))
        
        return {"name": "VisualEditorScenario", "steps": steps}

    def _strip_ids_recursive(self, data_list: list):
        """저장 전, UI에서만 사용되는 'id' 필드를 재귀적으로 제거합니다."""
        for item in data_list:
            if 'id' in item:
                del item['id']
            if item.get('type') == 'L' and isinstance(item.get('value'), list):
                self._strip_ids_recursive(item['value'])

    def export_to_master_scenario(self) -> dict:
        """현재 타임라인을 저장 가능한 master_scenario 형식으로 변환합니다."""
        steps = []
        sorted_items = sorted(
            [item for item in self.timeline_view.scene.items() if isinstance(item, ScenarioStepItem)],
            key=lambda item: item.y()
        )
        
        for item in sorted_items:
            # 원본 데이터가 바뀌지 않도록 깊은 복사를 합니다.
            step_data_copy = copy.deepcopy(item.step_data)

            # 복사된 데이터에서 'message' 객체의 'body' 내부의 모든 'id'를 제거합니다.
            if 'message' in step_data_copy and 'body' in step_data_copy['message']:
                self._strip_ids_recursive(step_data_copy['message']['body'])
            
            # UI에서만 사용되던 'device_type'과 'step_id'는 저장하지 않습니다.
            step_data_copy.pop('device_type', None)
            step_data_copy.pop('step_id', None)
            
            steps.append(step_data_copy)
        
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
            
            # ✅ 'wait_recv' 스텝을 올바르게 로드하기 위해 로직을 명확히 합니다.
            # 'wait_recv'가 있으면 device_id만 있어도 유효한 스텝입니다.
            if not device_id:
                continue

            # 'wait_recv'가 없는 'send' 스텝의 경우에만 메시지를 찾습니다.
            if 'wait_recv' not in step_data:
                # 로드된 데이터에 'message' 객체가 있는지 확인합니다.
                if 'message' in step_data:
                    message_body = step_data['message']
                # 없다면, message_id로 라이브러리에서 가져옵니다.
                elif message_id:
                    device_type = manager.get_device_type(device_id)
                    if device_type:
                        message_body = manager.get_message_body(device_type, message_id)
                    else:
                        message_body = None
                else:
                    continue
                
                if not message_body:
                    continue
                
                # 타임라인 아이템 생성을 위한 완전한 데이터 구성
                full_step_data = {
                    "device_id": device_id,
                    "delay": step_data.get("delay", 0.0),
                    "message_id": message_id,
                    "message": message_body,
                    "device_type": manager.get_device_type(device_id)
                }
            else: # 'wait_recv' 스텝은 그대로 사용합니다.
                full_step_data = step_data
                # device_type이 없을 수 있으므로 추가해줍니다.
                if 'device_type' not in full_step_data:
                    full_step_data['device_type'] = manager.get_device_type(device_id)


            item = ScenarioStepItem(full_step_data)
            item.signals.selected.connect(self.timeline_view.step_selected)
            self.timeline_view.scene.addItem(item)
            item.setPos(10, self.timeline_view.y_pos_counter)
            self.timeline_view.y_pos_counter += item.boundingRect().height() + 10