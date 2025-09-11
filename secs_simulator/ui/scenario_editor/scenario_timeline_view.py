# secs_simulator/ui/scenario_editor/scenario_timeline_view.py

from PySide6.QtWidgets import QGraphicsView, QGraphicsScene
from PySide6.QtCore import Signal, Slot

from .scenario_step_item import ScenarioStepItem

class ScenarioTimelineView(QGraphicsView):
    """
    드래그된 메시지를 드롭하여 ScenarioStepItem을 생성하고,
    선택된 아이템의 정보를 외부로 전달하는 뷰입니다.
    """
    # ✅ [핵심 수정] object 대신 명확한 타입의 시그널을 정의합니다.
    step_selected = Signal(ScenarioStepItem) 

    def __init__(self, scenario_manager, parent=None):
        super().__init__(parent)
        self.scenario_manager = scenario_manager
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setAcceptDrops(True)
        self.y_pos_counter = 10

    def dragEnterEvent(self, event):
        if event.mimeData().hasText() and event.mimeData().text().startswith("secs-message/"):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText() and event.mimeData().text().startswith("secs-message/"):
            event.acceptProposedAction()

    def dropEvent(self, event):
        """드롭 시 단순 QLabel 대신 ScenarioStepItem을 생성합니다."""
        mime_text = event.mimeData().text()
        if not mime_text.startswith("secs-message/"):
            return

        _, device_type, message_id = mime_text.split('/')
        
        message_body = self.scenario_manager.get_message_body(device_type, message_id)
        if not message_body:
            print(f"Warning: Message body for {device_type}/{message_id} not found.")
            return

        step_data = {
            "device_id": "Select Device...",
            "delay": 0.0,
            "message_id": message_id,
            "message": message_body,
            "device_type": device_type
        }
        
        item = ScenarioStepItem(step_data)
        # 아이템 내부의 'selected' 신호가 발생하면, 이 클래스의 'step_selected' 신호를 발생시킵니다.
        item.signals.selected.connect(self.step_selected.emit)
        
        self.scene.addItem(item)
        item.setPos(10, self.y_pos_counter)
        self.y_pos_counter += item.boundingRect().height() + 10

        event.acceptProposedAction()