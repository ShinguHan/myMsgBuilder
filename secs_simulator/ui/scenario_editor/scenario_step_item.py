# secs_simulator/ui/scenario_editor/scenario_step_item.py

import uuid
from PySide6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QTextDocument
from .helpers import StepItemSignals

class ScenarioStepItem(QGraphicsItem):
    """
    시나리오의 개별 스텝을 나타내며, 내부에 실제 데이터(딕셔너리)를 저장합니다.
    """

    def __init__(self, step_data: dict, parent: QGraphicsItem = None):
        super().__init__(parent)
        self.step_data = step_data
        if "step_id" not in self.step_data:
            self.step_data["step_id"] = str(uuid.uuid4())
            
        self.signals = StepItemSignals()

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        
        self.width = 200
        self.height = 50

    def boundingRect(self) -> QRectF:
        """이 아이템이 차지하는 영역을 정의합니다."""
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None):
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

        painter.save()
        
        device_id = self.step_data.get('device_id', 'Select Device...')
        message_id = self.step_data.get('message_id', 'N/A')
        html_text = f"""
        <div style='color: #E0E0E0;'>
            <b style='font-size: 14px;'>{device_id}</b>
            <p style='color: #AAAAAA; font-size: 12px; margin-top: 0px;'>{message_id}</p>
        </div>
        """

        doc = QTextDocument()
        doc.setHtml(html_text)
        doc.setTextWidth(self.width - 30)

        painter.translate(15, 10)
        doc.drawContents(painter)
        painter.restore()

    def mousePressEvent(self, event):
        """아이템을 클릭했을 때 'selected' 시그널을 발생시킵니다."""
        super().mousePressEvent(event)
        # 선택되었다는 신호를 외부(TimelineView)로 보냅니다.
        self.signals.selected.emit(self)