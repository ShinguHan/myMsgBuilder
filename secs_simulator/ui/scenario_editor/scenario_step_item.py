# secs_simulator/ui/scenario_editor/scenario_step_item.py
import uuid
from PySide6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QTextDocument, QFont

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
        self.height = 80 # 초기 기본 높이
        
        # ✅ [수정] 생성 시점의 텍스트로 첫 높이를 정확하게 계산합니다.
        self._calculate_height()

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self.width, self.height)

    def _get_display_html(self) -> str:
        """✅ [추가] 아이템에 표시될 HTML 콘텐츠를 생성하는 헬퍼 메서드입니다."""
        device_id = self.step_data.get('device_id', 'N/A')
        
        # Wait 액션 정보 구성
        if 'wait_recv' in self.step_data:
            s = self.step_data['wait_recv'].get('s', '?')
            f = self.step_data['wait_recv'].get('f', '?')
            title_text = f"<b>Wait for</b> S{s}F{f}"
            details_html = f"<p style='margin:0; font-size:12px;'>From: {device_id}</p>"
        # Send 액션 정보 구성
        elif 'message' in self.step_data:
            message_id = self.step_data.get('message_id', 'Custom Msg')
            delay = self.step_data.get('delay', 0.0)
            
            body = self.step_data["message"].get("body", [])
            item_count = 0
            if body:
                # L[<items>] 구조 고려
                if body[0].get('type') == 'L' and isinstance(body[0].get('value'), list):
                    item_count = len(body[0].get('value', []))
                else:
                    item_count = len(body)
            
            body_summary = f"{item_count} items"

            title_text = f"<b>Send</b>: {message_id}"
            details_html = f"""
                <p style='margin:0; font-size:12px;'>To: {device_id}</p>
                <p style='margin:0; font-size:11px; color:#AAAAAA;'>Delay: {delay:.1f}s | Body: {body_summary}</p>
            """
        # 그 외 (빈 스텝)
        else:
            title_text = "<b>Empty Step</b>"
            details_html = f"<p style='margin:0; font-size:12px;'>Device: {device_id}</p>"

        return f"""
        <div style='color: #E0E0E0; padding: 2px; font-size: 14px;'>
            {title_text}
            {details_html}
        </div>
        """

    def _calculate_height(self):
        """✅ [핵심 수정] 데이터 내용에 따라 아이템의 높이를 동적으로 계산합니다."""
        doc = QTextDocument()
        html = self._get_display_html()
        doc.setHtml(html)
        
        # 텍스트 너비를 아이템의 너비에서 좌우 여백을 뺀 값으로 설정
        # (아이콘 영역 40px + 텍스트 좌측 여백 5px + 우측 여백 5px)
        doc.setTextWidth(self.width - 50) 
        
        # 계산된 문서 높이에 상하 여백(padding) 16px를 더해 최종 높이로 설정
        self.height = doc.size().height() + 16

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None):
        """✅ [수정] paint 로직을 동적 높이에 맞게 단순화합니다."""
        rect = self.boundingRect()
        is_selected = self.isSelected()
        is_warning = self.step_data.get('device_id', 'N/A') == 'Select Device...'
        
        bg_color = "#3478F6" if is_selected else "#1E1E1E"
        border_color = "#FFA500" if is_warning else ("#508FF7" if is_selected else "#454545")
        
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(border_color), 1.5))
        painter.setBrush(QBrush(QColor(bg_color)))
        painter.drawRoundedRect(rect, 8.0, 8.0)

        painter.save()
        
        # --- 아이콘 그리기 ---
        icon_font = QFont("Arial", 16)
        painter.setFont(icon_font)
        icon = "⏳" if 'wait_recv' in self.step_data else ("📤" if 'message' in self.step_data else "❓")
        painter.drawText(QRectF(10, 8, 30, 30), Qt.AlignmentFlag.AlignHCenter, icon)

        # --- 텍스트 내용 그리기 ---
        doc = QTextDocument()
        doc.setHtml(self._get_display_html())
        doc.setTextWidth(self.width - 50)
        
        # 텍스트를 아이콘 오른쪽, 상하 중앙에 가깝게 배치
        painter.translate(45, 8)
        doc.drawContents(painter)

        painter.restore()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.signals.position_changed.emit(self)
        
    def update_visuals(self):
        """외부에서 호출하여 아이템의 모양과 내용을 갱신합니다."""
        # 중요: 지오메트리(크기, 모양) 변경이 있을 것임을 미리 시스템에 알립니다.
        self.prepareGeometryChange()
        # 새로운 데이터에 맞춰 높이를 다시 계산합니다.
        self._calculate_height()
        # 아이템을 다시 그리도록 요청합니다.
        self.update()