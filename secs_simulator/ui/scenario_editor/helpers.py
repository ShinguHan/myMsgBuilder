from PySide6.QtCore import Signal, QObject
from PySide6.QtWidgets import QGraphicsItem

class StepItemSignals(QObject):
    """QGraphicsItem에서 시그널을 보내기 위한 헬퍼 클래스"""
    selected = Signal(QGraphicsItem)
