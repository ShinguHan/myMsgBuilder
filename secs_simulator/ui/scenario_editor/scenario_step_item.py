# secs_simulator/ui/scenario_editor/scenario_step_item.py

import uuid
from PySide6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QTextDocument, QFont
import json

from .helpers import StepItemSignals

class ScenarioStepItem(QGraphicsItem):
    """'Send'와 'Wait' 액션을 모두 시각적으로 표현하는 시나리오 스텝 아이템입니다."""

    def __init__(self, step_data: dict, parent: QGraphicsItem = None):
        super().__init__(parent)
        self.step_data = step_data
        if "id" not in self.step_data:
            self.step_data["id"] = str(uuid.uuid4())
            
        self.signals = StepItemSignals()

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        
        self.width = 240
        self._calculate_height()

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.width, self.height)

    def _calculate_height(self):
        """데이터 내용에 따라 아이템의 높이를 동적으로 계산합니다."""
        # ✅ [핵심 수정] wait_recv와 message의 존재 여부에 따라 높이를 다르게 설정합니다.
        is_wait = 'wait_recv' in self.step_data
        is_send = 'message' in self.step_data and self.step_data['message']

        if is_wait and not is_send: # Wait 전용 스텝
            self.height = 70
        elif not is_wait and is_send: # Send 전용 스텝
            body = self.step_data.get("message", {}).get("body", [])
            body_line_count = 1 if body else 0
            self.height = 80 + (body_line_count * 15)
        else: # 기본 또는 오류 상태
            self.height = 50

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None):
        """✅ [핵심 수정] Send와 Wait 상태를 구분하여 그립니다."""
        rect = self.boundingRect()
        
        # 선택 상태에 따른 브러시 및 펜 설정
        is_selected = self.isSelected()
        bg_color = "#3478F6" if is_selected else "#1E1E1E"
        border_color = "#508FF7" if is_selected else "#454545"
        
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(border_color), 1))
        painter.setBrush(QBrush(QColor(bg_color)))
        painter.drawRoundedRect(rect, 8.0, 8.0)

        painter.save()
        
        device_id = self.step_data.get('device_id', 'N/A')
        delay = self.step_data.get('delay', 0.0)
        
        # --- 아이콘 및 제목 ---
        icon_font = QFont("Arial", 16)
        painter.setFont(icon_font)
        
        if 'wait_recv' in self.step_data:
            # Wait 액션일 경우
            icon = "⏳"
            s = self.step_data['wait_recv'].get('s', '?')
            f = self.step_data['wait_recv'].get('f', '?')
            timeout = self.step_data.get('timeout', 10)
            title_text = f"Wait for S{s}F{f}"
            details_html = f"""
                <p style='color: #AAAAAA; font-size: 12px; margin: 0;'>Device: {device_id}</p>
                <p style='color: #FFCC00; font-size: 12px; margin: 0;'>Timeout: {timeout:.1f}s</p>
            """
        elif 'message' in self.step_data:
            # Send 액션일 경우
            icon = "📤"
            message_id = self.step_data.get('message_id', 'Custom Msg')
            title_text = f"Send: {message_id}"
            body = self.step_data["message"].get("body", [])
            body_preview = json.dumps(body)
            body_preview = (body_preview[:35] + '...') if len(body_preview) > 35 else body_preview
            details_html = f"""
                <p style='color: #AAAAAA; font-size: 12px; margin: 0;'>To: {device_id}</p>
                <p style='color: #FFCC00; font-size: 12px; margin: 0;'>Delay: {delay:.1f}s</p>
                <p style='color: #77DD77; font-size: 10px; margin: 0; font-family: Courier New;'>{body_preview}</p>
            """
        else: # 기본 상태
            icon = "❓"
            title_text = "Empty Step"
            details_html = ""

        painter.drawText(QRectF(10, 5, 30, 30), Qt.AlignmentFlag.AlignCenter, icon)

        # --- 텍스트 내용 ---
        main_text_html = f"""
        <div style='color: #E0E0E0; padding: 2px;'>
            <b style='font-size: 14px;'>{title_text}</b>
            {details_html}
        </div>
        """
        
        doc = QTextDocument()
        doc.setHtml(main_text_html)
        doc.setTextWidth(self.width - 50) 
        
        painter.translate(45, 5) # 아이콘 옆으로 텍스트 위치 조정
        doc.drawContents(painter)

        painter.restore()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.signals.position_changed.emit(self)
        
    def update_visuals(self):
        self.prepareGeometryChange()
        self._calculate_height()
        self.update()

