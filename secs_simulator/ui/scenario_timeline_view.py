from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QLabel
from PySide6.QtCore import Qt

class ScenarioTimelineView(QGraphicsView):
    """
    드래그된 메시지를 드롭하여 시나리오 스텝을 생성하는 뷰입니다.
    Qt의 강력한 2D 그래픽 시스템(Graphics View Framework)을 사용합니다.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setAcceptDrops(True)  # 이 위젯이 드롭 이벤트를 받을 수 있도록 설정
        self.y_pos_counter = 10  # 스텝이 쌓일 y 좌표

    def dragEnterEvent(self, event):
        """드래그된 아이템이 우리 뷰 영역에 들어왔을 때 호출됩니다."""
        # 우리가 정의한 "secs-message/" 형식의 텍스트 데이터가 맞는지 확인합니다.
        if event.mimeData().hasText() and event.mimeData().text().startswith("secs-message/"):
            event.acceptProposedAction() # 드롭을 허용합니다.

    def dragMoveEvent(self, event):
        """드래그된 아이템이 뷰 영역 안에서 움직일 때 호출됩니다."""
        if event.mimeData().hasText() and event.mimeData().text().startswith("secs-message/"):
            event.acceptProposedAction()

    def dropEvent(self, event):
        """아이템이 최종적으로 드롭되었을 때 실행되는 로직입니다."""
        mime_text = event.mimeData().text()
        if not mime_text.startswith("secs-message/"):
            return

        # "secs-message/CV/S1F1_AreYouThere" 형식의 데이터를 파싱합니다.
        parts = mime_text.split('/')
        if len(parts) == 3:
            device_type = parts[1]
            message_id = parts[2]
            
            # 드롭된 위치에 시각적인 스텝 아이템(지금은 간단한 라벨)을 추가합니다.
            step_label = QLabel(f"<b>{device_type}</b>: {message_id}")
            step_label.setStyleSheet("background-color: #e8f4ff; border: 1px solid #007bff; padding: 10px; border-radius: 5px;")
            
            # QGraphicsScene은 위젯을 직접 담을 수 있으므로 addWidget을 사용합니다.
            proxy_widget = self.scene.addWidget(step_label)
            # 아이템들이 순서대로 쌓이도록 y 좌표를 조정합니다.
            proxy_widget.setPos(10, self.y_pos_counter) 
            self.y_pos_counter += proxy_widget.boundingRect().height() + 10

            event.acceptProposedAction()
