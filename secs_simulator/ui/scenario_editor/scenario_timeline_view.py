from PySide6.QtWidgets import QGraphicsView, QGraphicsScene
from PySide6.QtCore import Signal, Qt

# 방금 만든 ScenarioStepItem을 임포트합니다.
from .scenario_step_item import ScenarioStepItem

class ScenarioTimelineView(QGraphicsView):
    """
    드래그된 메시지를 드롭하여 ScenarioStepItem을 생성하는 뷰입니다.
    """
    # 선택된 스텝 아이템의 정보를 외부(PropertyEditor)로 전달하기 위한 시그널
    step_selected = Signal(object) 

    def __init__(self, scenario_manager, parent=None):
        super().__init__(parent)
        self.scenario_manager = scenario_manager # 메시지 정보를 가져오기 위해 필요
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
        
        # ScenarioManager를 통해 메시지의 전체 정보(body 등)를 가져옵니다.
        # 이 get_message_body 메소드는 잠시 후에 ScenarioManager에 추가할 것입니다.
        message_body = self.scenario_manager.get_message_body(device_type, message_id)
        if not message_body:
            print(f"Warning: Message body for {device_type}/{message_id} not found.")
            return

        # ScenarioStepItem이 가질 초기 데이터 모델을 생성합니다.
        step_data = {
            "device_id": "Select Device...", # 기본값
            "delay": 0.0,
            "message_id": message_id,
            "message": message_body,
            "device_type": device_type # PropertyEditor에서 사용될 정보
        }
        
        # 데이터와 함께 똑똑한 아이템을 생성합니다.
        item = ScenarioStepItem(step_data)
        # 아이템이 클릭되면, step_selected 시그널을 통해 자신의 정보를 외부에 알립니다.
        item.signals.selected.connect(self.step_selected.emit)
        self.scene.addItem(item)
        
        item.setPos(10, self.y_pos_counter)
        self.y_pos_counter += item.boundingRect().height() + 10

        event.acceptProposedAction()

