# secs_simulator/ui/scenario_editor/scenario_step_item.py

import uuid
from PySide6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QTextDocument
import json

from .helpers import StepItemSignals

class ScenarioStepItem(QGraphicsItem):
    """모든 상세 정보를 표시하는 시나리오 스텝 아이템입니다."""

    def __init__(self, step_data: dict, parent: QGraphicsItem = None):
        super().__init__(parent)
        self.step_data = step_data
        if "step_id" not in self.step_data:
            self.step_data["step_id"] = str(uuid.uuid4())
            
        self.signals = StepItemSignals()

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        
        self.width = 220
        self.height = 100 # 초기 높이
        
        # 생성 시점의 데이터로 첫 높이를 계산합니다.
        self._calculate_height()

    def boundingRect(self) -> QRectF:
        """이 아이템이 차지하는 영역을 시스템에 알립니다."""
        return QRectF(0, 0, self.width, self.height)

    def _calculate_height(self):
        """
        현재 데이터에 기반하여 아이템의 정확한 높이를 계산합니다.
        """
        doc = QTextDocument()
        doc.setHtml(self._generate_html())
        doc.setTextWidth(self.width - 20)
        self.height = doc.size().height() + 10

    # ✅ [기능 추가] 사용자가 아이템을 움직인 후 마우스를 놓으면 신호를 보냅니다.
    def mouseReleaseEvent(self, event):
        """마우스 버튼을 놓았을 때, 위치 변경이 완료되었음을 알립니다."""
        super().mouseReleaseEvent(event)
        self.signals.position_changed.emit()

    def _generate_html(self) -> str:
        """현재 데이터로 표시할 HTML을 생성합니다."""
        device_id = self.step_data.get('device_id', 'Select Device...')
        message_id = self.step_data.get('message_id', 'N/A')
        delay = self.step_data.get('delay', 0.0)

        body_preview = ""
        message = self.step_data.get("message", {})
        if isinstance(message, dict) and "body" in message and message["body"]:
            try:
                # 가독성을 위해 indent를 2로 설정
                body_str = json.dumps(message["body"], indent=2)
                # 미리보기 길이를 늘려서 더 많은 정보를 표시
                body_preview = (body_str[:150] + '...') if len(body_str) > 150 else body_str
            except TypeError:
                body_preview = "Invalid body structure"
        
        # HTML 태그의 오타를 수정하고 pre 태그로 감싸서 공백을 유지합니다.
        return f"""
        <div style='color: #E0E0E0; padding: 2px;'>
            <b style='font-size: 14px;'>{device_id}</b><br>
            <span style='color: #AAAAAA; font-size: 12px;'>Msg: {message_id}</span><br>
            <span style='color: #FFCC00; font-size: 12px;'>Delay: {delay:.1f}s</span>
            <pre style='color: #77DD77; font-size: 10px; margin: 0; font-family: Courier New;'>{body_preview}</pre>
        </div>
        """

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None):
        """아이템을 화면에 그립니다."""
        rect = self.boundingRect()
        
        if self.isSelected():
            brush = QBrush(QColor("#3478F6"))
            pen = QPen(QColor("#508FF7"), 1)
        else:
            brush = QBrush(QColor("#1E1E1E"))
            pen = QPen(QColor("#454545"), 1)

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(pen)
        painter.setBrush(brush)
        painter.drawRoundedRect(rect, 8.0, 8.0)
        
        doc = QTextDocument()
        doc.setHtml(self._generate_html())
        doc.setTextWidth(self.width - 20)
        
        painter.translate(10, 5)
        doc.drawContents(painter)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.signals.selected.emit(self)

    def update_visuals(self):
        """
        [핵심 수정]
        데이터 변경 후 외부에서 호출하는 공식 업데이트 메서드입니다.
        예제 코드의 로직과 동일한 순서로 실행됩니다.
        """
        # 1. 시스템에 아이템의 크기가 곧 변경될 것임을 '미리' 알립니다.
        self.prepareGeometryChange()
        
        # 2. 새로운 데이터에 맞춰 자신의 높이를 다시 계산합니다.
        # (데이터 자체는 property_editor에서 이미 변경된 상태입니다)
        self._calculate_height()
        
        # 3. 화면을 다시 그리도록 요청합니다. (paint 호출)
        self.update()

