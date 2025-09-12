from PySide6.QtWidgets import QGraphicsView, QGraphicsScene
from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QKeyEvent, QBrush, QColor, QPainter
import copy
import uuid

from .scenario_step_item import ScenarioStepItem
from secs_simulator.engine.scenario_manager import ScenarioManager

class ScenarioTimelineView(QGraphicsView):
    """
    드래그된 메시지를 드롭하여 ScenarioStepItem을 생성하고,
    자동 정렬 및 사용자 상호작용을 처리하는 지능적인 뷰입니다.
    """
    step_selected = Signal(ScenarioStepItem)
    step_deleted = Signal()

    def __init__(self, scenario_manager: ScenarioManager, parent=None):
        super().__init__(parent)
        self.scenario_manager = scenario_manager
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setAcceptDrops(True)

        # --- UX 개선 ---
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setBackgroundBrush(QBrush(QColor("#2D2D2D")))
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag) # 드래그로 다중 선택 가능

    def _create_step_item(self, step_data: dict) -> ScenarioStepItem:
        """ScenarioStepItem을 생성하고 필요한 신호를 연결하는 헬퍼 함수입니다."""
        item = ScenarioStepItem(step_data)
        item.signals.selected.connect(self.step_selected)
        item.signals.position_changed.connect(self._rearrange_items)
        return item

    def _rearrange_items(self):
        """타임라인의 모든 아이템을 y좌표 기준으로 재정렬합니다."""
        y_pos = 10
        items = sorted(
            [item for item in self.scene.items() if isinstance(item, ScenarioStepItem)],
            key=lambda item: item.y()
        )
        for item in items:
            item.setPos(10, y_pos)
            y_pos += item.boundingRect().height() + 10
        
        # 스크롤바가 올바르게 동작하도록 씬의 영역을 업데이트합니다.
        self.setSceneRect(self.scene.itemsBoundingRect())

    def _assign_new_ids_recursive(self, data_list: list):
        """메시지 body 데이터에 새로운 고유 ID를 재귀적으로 할당합니다."""
        for item in data_list:
            item['id'] = str(uuid.uuid4())
            if item.get('type') == 'L' and isinstance(item.get('value'), list):
                self._assign_new_ids_recursive(item['value'])

    def keyPressEvent(self, event: QKeyEvent):
        """키보드 입력을 처리하여 삭제 및 복제 기능을 구현합니다."""
        if event.key() == Qt.Key.Key_Delete:
            selected_items = self.scene.selectedItems()
            if not selected_items:
                return
            
            for item in selected_items:
                self.scene.removeItem(item)
            
            self._rearrange_items()
            self.step_deleted.emit()

        elif event.key() == Qt.Key.Key_D and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            selected_items = self.scene.selectedItems()
            if not selected_items:
                return

            new_items = []
            for item in selected_items:
                new_step_data = copy.deepcopy(item.step_data)
                if 'message' in new_step_data and 'body' in new_step_data['message']:
                    self._assign_new_ids_recursive(new_step_data['message']['body'])
                
                new_item = self._create_step_item(new_step_data)
                self.scene.addItem(new_item)
                # 복제된 아이템을 원본 바로 아래에 위치시킵니다. (정렬 전 임시 위치)
                new_item.setPos(10, item.y() + item.boundingRect().height() + 15)
                new_items.append(new_item)

            self._rearrange_items()

            # 기존 선택을 해제하고 새로 복제된 아이템들을 선택합니다.
            for item in selected_items:
                item.setSelected(False)
            for item in new_items:
                item.setSelected(True)
            
            if new_items:
                self.ensureVisible(new_items[-1]) # 마지막으로 복제된 아이템이 보이도록 스크롤
        
        else:
            super().keyPressEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText() and event.mimeData().text().startswith("secs-message/"):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText() and event.mimeData().text().startswith("secs-message/"):
            event.acceptProposedAction()

    def dropEvent(self, event):
        mime_text = event.mimeData().text()
        if not mime_text.startswith("secs-message/"):
            return

        _, device_type, message_id = mime_text.split('/')
        
        message_body = self.scenario_manager.get_message_body(device_type, message_id)
        if not message_body:
            return

        step_data = {
            "device_id": "Select Device...",
            "delay": 0.0,
            "message_id": message_id,
            "message": message_body,
            "device_type": device_type
        }
        
        item = self._create_step_item(step_data)
        
        # 드롭된 위치에 아이템을 임시로 놓습니다.
        drop_pos = self.mapToScene(event.pos())
        item.setPos(10, drop_pos.y())
        
        self.scene.addItem(item)
        
        self._rearrange_items() # 즉시 전체 재정렬
        self.ensureVisible(item) # 추가된 아이템이 보이도록 스크롤

        event.acceptProposedAction()

    def load_from_scenario_data(self, scenario_data: dict):
        self.scene.clear()
        self.property_editor.clear_view()

        manager = self.scenario_manager
        for step_data in scenario_data.get("steps", []):
            # message가 통째로 저장된 경우
            if "message" in step_data:
                full_step_data = copy.deepcopy(step_data)
            # message_id만 저장된 경우 (하위 호환성)
            elif "message_id" in step_data:
                device_id = step_data.get("device_id")
                message_id = step_data.get("message_id")
                if not all([device_id, message_id]): continue

                device_type = manager.get_device_type(device_id)
                if not device_type: continue

                message_body = manager.get_message_body(device_type, message_id)
                if not message_body: continue
                
                full_step_data = {**step_data, "message": message_body, "device_type": device_type}
            else:
                continue

            item = self._create_step_item(full_step_data)
            self.scene.addItem(item)
            
        self._rearrange_items()

