from PySide6.QtWidgets import QGraphicsView, QGraphicsScene
from PySide6.QtCore import Signal, Qt, Slot
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
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)

        # ✅ [최종 수정] Scene의 내장 selectionChanged 신호를 직접 슬롯에 연결합니다.
        # 이것이 아이템 선택을 감지하는 가장 확실한 방법입니다.
        self.scene.selectionChanged.connect(self._on_selection_changed)

    @Slot()
    def _on_selection_changed(self):
        """✅ [최종 수정] Scene에서 선택된 아이템이 변경될 때 호출되는 슬롯."""
        selected_items = self.scene.selectedItems()
        
        # 오직 하나의 아이템만 선택되었을 경우에만 속성 편집기에 정보를 표시합니다.
        if len(selected_items) == 1:
            item = selected_items[0]
            if isinstance(item, ScenarioStepItem):
                self.step_selected.emit(item)
        else:
            # 여러 개가 선택되거나 아무것도 선택되지 않으면 속성 편집기를 비웁니다.
            self.step_deleted.emit()

    def _create_step_item(self, step_data: dict) -> ScenarioStepItem:
        """ScenarioStepItem을 생성하고 필요한 신호를 연결하는 헬퍼 함수입니다."""
        item = ScenarioStepItem(step_data)
        # ❌ 이전의 잘못된 연결 코드를 제거합니다. Scene의 selectionChanged가 이 역할을 대신합니다.
        # item.signals.selected.connect(self.step_selected.emit) 
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
            # ✅ self.step_deleted.emit()을 여기서 호출할 필요 없습니다.
            # removeItem에 의해 selectionChanged가 자동으로 발생하여 처리됩니다.

        elif event.key() == Qt.Key.Key_D and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            selected_items = self.scene.selectedItems()
            if not selected_items:
                return

            new_items = []
            for item in selected_items:
                new_step_data = copy.deepcopy(item.step_data)
                new_step_data['id'] = str(uuid.uuid4())
                if 'message' in new_step_data and 'body' in new_step_data['message']:
                    self._assign_new_ids_recursive(new_step_data['message']['body'])
                
                new_item = self._create_step_item(new_step_data)
                self.scene.addItem(new_item)
                new_item.setPos(10, item.y() + item.boundingRect().height() + 15)
                new_items.append(new_item)

            self._rearrange_items()

            for item in selected_items:
                item.setSelected(False)
            for item in new_items:
                item.setSelected(True)
            
            if new_items:
                self.ensureVisible(new_items[-1])
        
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
        
        drop_pos = self.mapToScene(event.pos())
        item.setPos(10, drop_pos.y())
        
        self.scene.addItem(item)
        
        self._rearrange_items()
        self.ensureVisible(item)

        event.acceptProposedAction()

    def load_from_scenario_data(self, scenario_data: dict):
        self.scene.clear()
        
        manager = self.scenario_manager
        for step_data in scenario_data.get("steps", []):
            full_step_data = copy.deepcopy(step_data)
            
            if 'device_type' not in full_step_data:
                 device_id = full_step_data.get("device_id")
                 if device_id:
                     full_step_data['device_type'] = manager.get_device_type(device_id)

            if 'wait_recv' in full_step_data or 'message' in full_step_data:
                pass
            elif "message_id" in full_step_data:
                device_id = full_step_data.get("device_id")
                message_id = full_step_data.get("message_id")
                device_type = manager.get_device_type(device_id)
                
                if device_type and message_id:
                    message_body = manager.get_message_body(device_type, message_id)
                    if message_body:
                        full_step_data['message'] = message_body
                    else: continue
                else: continue
            else:
                continue

            item = self._create_step_item(full_step_data)
            self.scene.addItem(item)
            
        self._rearrange_items()
