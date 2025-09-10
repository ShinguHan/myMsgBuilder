import uuid
from PySide6.QtWidgets import QGraphicsItem, QStyleOptionGraphicsItem, QWidget
from PySide6.QtCore import QRectF, Qt, Signal, QObject
from PySide6.QtGui import QPainter, QColor, QPen, QBrush

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
        """아이템을 화면에 그리는 로직입니다."""
        rect = self.boundingRect()
        
        # 선택되었을 때와 아닐 때 배경색을 다르게 설정
        brush = QBrush(QColor("#e8f4ff") if self.isSelected() else QColor("white"))
        painter.setBrush(brush)
        
        pen = QPen(QColor("#007bff") if self.isSelected() else QColor("#adb5bd"), 2)
        painter.setPen(pen)
        
        painter.drawRoundedRect(rect, 5.0, 5.0)

        # 아이템에 텍스트(Device ID, Message ID)를 표시
        painter.setPen(Qt.GlobalColor.black)
        device_id = self.step_data.get('device_id', 'N/A')
        message_id = self.step_data.get('message_id', 'N/A')
        text = f"<b>{device_id}</b><br>{message_id}"
        painter.drawText(rect.adjusted(10, 5, -10, -5), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)

    def mousePressEvent(self, event):
        """아이템을 클릭했을 때 'selected' 시그널을 발생시킵니다."""
        super().mousePressEvent(event)
        self.signals.selected.emit(self)
