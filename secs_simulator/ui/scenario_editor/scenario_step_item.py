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
        is_wait = 'wait_recv' in self.step_data
        is_send = 'message' in self.step_data and self.step_data['message']

        if is_wait and not is_send: # Wait 전용 스텝
            self.height = 70
        elif not is_wait and is_send: # Send 전용 스텝
            self.height = 80
        else: # 기본 또는 오류 상태
            self.height = 50

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None):
        """✅ [개선] Send/Wait 상태 및 경고 상태를 구분하여 그립니다."""
        rect = self.boundingRect()
        
        is_selected = self.isSelected()
        
        # ✅ 1. 상태 표시: Device ID가 설정되지 않았으면 경고 상태로 표시
        is_warning = self.step_data.get('device_id', 'N/A') == 'Select Device...'
        
        bg_color = "#3478F6" if is_selected else "#1E1E1E"
        # 경고 상태일 경우 테두리 색상을 주황색으로, 선택 시 밝은 주황색으로 변경
        if is_warning:
            border_color = "#FFA500" if not is_selected else "#FFC56E"
        else:
            border_color = "#508FF7" if is_selected else "#454545"
        
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(border_color), 1.5)) # 테두리 두께 강조
        painter.setBrush(QBrush(QColor(bg_color)))
        painter.drawRoundedRect(rect, 8.0, 8.0)

        painter.save()
        
        device_id = self.step_data.get('device_id', 'N/A')
        
        # --- 아이콘 및 제목 ---
        icon_font = QFont("Arial", 16)
        painter.setFont(icon_font)
        
        # ✅ 2. 정보 요약 및 시각화 (Wait)
        if 'wait_recv' in self.step_data:
            icon = "⏳"
            s = self.step_data['wait_recv'].get('s', '?')
            f = self.step_data['wait_recv'].get('f', '?')
            title_text = f"<b>Wait for</b> S{s}F{f}"
            details_html = f"<p style='margin:0; font-size:12px;'>From: {device_id}</p>"
        # ✅ 2. 정보 요약 및 시각화 (Send)
        elif 'message' in self.step_data:
            icon = "📤"
            message_id = self.step_data.get('message_id', 'Custom Msg')
            delay = self.step_data.get('delay', 0.0)
            
            body = self.step_data["message"].get("body", [])
            body_item_count = len(body[0].get('value', [])) if body and body[0].get('type') == 'L' else len(body)
            body_summary = f"L [{body_item_count} items]" if body and body[0].get('type') == 'L' else f"Body [{len(body)} items]"

            title_text = f"<b>Send</b>: {message_id}"
            details_html = f"""
                <p style='margin:0; font-size:12px;'>To: {device_id}</p>
                <p style='margin:0; font-size:11px; color:#AAAAAA;'>Delay: {delay:.1f}s | {body_summary}</p>
            """
        else:
            icon = "❓"
            title_text = "Empty Step"
            details_html = ""

        painter.drawText(QRectF(10, 5, 30, 30), Qt.AlignmentFlag.AlignCenter, icon)

        # --- 텍스트 내용 ---
        main_text_html = f"""
        <div style='color: #E0E0E0; padding: 2px; font-size: 14px;'>
            {title_text}
            {details_html}
        </div>
        """
        
        doc = QTextDocument()
        doc.setHtml(main_text_html)
        doc.setTextWidth(self.width - 50) 
        
        painter.translate(45, 8)
        doc.drawContents(painter)

        painter.restore()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.signals.position_changed.emit(self)
        
    def update_visuals(self):
        """외부에서 호출하여 아이템의 모양과 내용을 갱신합니다."""
        self.prepareGeometryChange()
        self._calculate_height()
        self.update()