from PySide6.QtWidgets import QGraphicsView, QGraphicsScene
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QKeyEvent
import copy
import uuid

from .scenario_step_item import ScenarioStepItem
from secs_simulator.engine.scenario_manager import ScenarioManager

class ScenarioTimelineView(QGraphicsView):
    """
    드래그된 메시지를 드롭하여 ScenarioStepItem을 생성하고,
    선택, 삭제, 복제 등의 상호작용을 처리하는 뷰입니다.
    """
    step_selected = Signal(ScenarioStepItem)
    # ✅ [기능 추가] 스텝이 삭제되었을 때 알리는 신호
    step_deleted = Signal()

    def __init__(self, scenario_manager: ScenarioManager, parent=None):
        super().__init__(parent)
        self.scenario_manager = scenario_manager
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setAcceptDrops(True)
        self.y_pos_counter = 10

    def _assign_new_ids_recursive(self, data_list: list):
        """메시지 body 데이터에 새로운 고유 ID를 재귀적으로 할당합니다."""
        for item in data_list:
            item['id'] = str(uuid.uuid4())
            if item.get('type') == 'L' and isinstance(item.get('value'), list):
                self._assign_new_ids_recursive(item['value'])

    def _rearrange_items(self):
        """타임라인의 모든 아이템을 y좌표 기준으로 재정렬합니다."""
        self.y_pos_counter = 10
        sorted_items = sorted(
            [item for item in self.scene.items() if isinstance(item, ScenarioStepItem)],
            key=lambda item: item.y()
        )
        for item in sorted_items:
            item.setPos(10, self.y_pos_counter)
            self.y_pos_counter += item.boundingRect().height() + 10

    def keyPressEvent(self, event: QKeyEvent):
        """키보드 입력을 처리하여 삭제 및 복제 기능을 구현합니다."""
        # ✅ [기능 추가] Delete 키로 선택된 아이템 삭제
        if event.key() == Qt.Key.Key_Delete:
            selected_items = self.scene.selectedItems()
            if not selected_items:
                return
            
            for item in selected_items:
                self.scene.removeItem(item)
            
            self._rearrange_items()
            self.step_deleted.emit() # 속성 창을 비우도록 신호 전송

        # ✅ [기능 추가] Ctrl+D 단축키로 아이템 복제
        elif event.key() == Qt.Key.Key_D and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            selected_items = self.scene.selectedItems()
            if not selected_items:
                return

            # 가장 아래에 있는 아이템을 기준으로 복제 위치를 잡습니다.
            last_item = max(selected_items, key=lambda item: item.y())

            for item in selected_items:
                new_step_data = copy.deepcopy(item.step_data)
                
                # 복제된 아이템의 메시지 Body에 새로운 ID를 부여합니다.
                if 'message' in new_step_data and 'body' in new_step_data['message']:
                    self._assign_new_ids_recursive(new_step_data['message']['body'])
                
                new_item = ScenarioStepItem(new_step_data)
                new_item.signals.selected.connect(self.step_selected)
                self.scene.addItem(new_item)
                # 복제된 아이템을 원본 바로 아래에 위치시킵니다.
                new_item.setPos(10, last_item.y() + last_item.boundingRect().height() + 10)
            
            self._rearrange_items()
        
        else:
            super().keyPressEvent(event)

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
