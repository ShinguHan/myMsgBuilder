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
        
        # ✅ 더 많은 정보를 표시하기 위해 높이를 90으로 늘립니다.
        self.width = 220
        self.height = 90

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None):
        """✅ Device ID, Message ID, Delay, Body Preview를 모두 그립니다."""
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
        
        # 데이터 모델에서 최신 정보를 가져옵니다.
        device_id = self.step_data.get('device_id', 'Select Device...')
        message_id = self.step_data.get('message_id', 'N/A')
        delay = self.step_data.get('delay', 0.0)

        # message body 요약 (JSON 형식으로 간단히 표시)
        body_preview = ""
        message = self.step_data.get("message", {})
        if isinstance(message, dict) and "body" in message and message["body"]:
            try:
                # json.dumps를 사용해 좀 더 깔끔하게 표현
                body_str = json.dumps(message["body"])
                body_preview = (body_str[:35] + '...') if len(body_str) > 35 else body_str
            except TypeError:
                body_preview = "Invalid body structure"
        
        html_text = f"""
        <div style='color: #E0E0E0; padding: 2px;'>
            <b style='font-size: 14px;'>{device_id}</b>
            <p style='color: #AAAAAA; font-size: 12px; margin: 0;'>Msg: {message_id}</p>
            <p style='color: #FFCC00; font-size: 12px; margin: 0;'>Delay: {delay:.1f}s</p>
            <p style='color: #77DD77; font-size: 10px; margin: 0; font-family: Courier New;'>{body_preview}</p>
        </div>
        """

        doc = QTextDocument()
        doc.setHtml(html_text)
        doc.setTextWidth(self.width - 20)

        painter.translate(10, 5)
        doc.drawContents(painter)

        painter.restore()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        self.signals.selected.emit(self)