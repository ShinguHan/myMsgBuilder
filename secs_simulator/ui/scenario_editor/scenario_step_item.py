import uuid
from PySide6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget
from PySide6.QtCore import QRectF, Qt, Signal, QObject
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QTextDocument
# ✅ 여기에 누락되었던 헬퍼 클래스 임포트 구문을 추가합니다.
from .helpers import StepItemSignals

class StepItemSignals(QObject):
    """QGraphicsItem에서 시그널을 보내기 위한 헬퍼 클래스"""
    selected = Signal(QGraphicsItem)

class ScenarioStepItem(QGraphicsItem):
    """
    시나리오의 개별 스텝을 나타내며, 내부에 실제 데이터(딕셔너리)를 저장합니다.
    """

    def __init__(self, step_data: dict, parent: QGraphicsItem = None):
        super().__init__(parent)
        self.step_data = step_data
        # 모든 스텝에 고유 ID를 부여하여 구분합니다.
        if "step_id" not in self.step_data:
            self.step_data["step_id"] = str(uuid.uuid4())
            
        self.signals = StepItemSignals()

        # 아이템을 선택하고 움직일 수 있도록 설정합니다 (향후 순서 변경 대비)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        
        self.width = 200
        self.height = 50

    def boundingRect(self) -> QRectF:
        """이 아이템이 차지하는 영역을 정의합니다."""
        return QRectF(0, 0, self.width, self.height)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget: QWidget = None):
        # ... (기존의 rect, brush, pen 설정은 그대로 둡니다)
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

        # ❌ 기존 코드 (HTML 태그가 그대로 보임)
        # device_id = self.step_data.get('device_id', 'N/A')
        # message_id = self.step_data.get('message_id', 'N/A')
        # text = f"<b>{device_id}</b><br>{message_id}"
        # painter.drawText(...)

        # ✅ 수정된 코드 (HTML을 올바르게 렌더링)
        painter.save() # 현재 화가 상태 저장
        
        # 1. HTML 텍스트 준비 (스타일까지 포함)
        device_id = self.step_data.get('device_id', 'Select Device...')
        message_id = self.step_data.get('message_id', 'N/A')
        html_text = f"""
        <div style='color: #E0E0E0;'>
            <b style='font-size: 14px;'>{device_id}</b>
            <p style='color: #AAAAAA; font-size: 12px; margin-top: 0px;'>{message_id}</p>
        </div>
        """

        # 2. QTextDocument를 사용하여 HTML을 그립니다.
        doc = QTextDocument()
        doc.setHtml(html_text)
        doc.setTextWidth(self.width - 30) # 자동 줄바꿈을 위한 너비 설정

        # 3. 텍스트를 그릴 위치를 정하고 그립니다.
        painter.translate(15, 10) # 왼쪽 상단으로 붓 이동
        doc.drawContents(painter)

        painter.restore() # 저장했던 화가 상태 복원

    def mousePressEvent(self, event):
        """아이템을 클릭했을 때 'selected' 시그널을 발생시킵니다."""
        super().mousePressEvent(event)
        self.signals.selected.emit(self)
