from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QLabel
from PySide6.QtCore import Qt

class ScenarioTimelineView(QGraphicsView):
    """드래그된 메시지를 드롭하여 시나리오 스텝을 생성하는 뷰입니다."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setAcceptDrops(True)  # 드롭 기능 활성화
        self.y_pos_counter = 10  # 스텝이 쌓일 y 좌표

    def dragEnterEvent(self, event):
        """드래그된 아이템이 우리 뷰에 들어왔을 때 유효성을 검사합니다."""
        mime_data = event.mimeData()
        if mime_data.hasFormat('application/x-qabstractitemmodeldatalist'):
            # MessageLibraryView에서 온 아이템인지 간단히 확인
            event.acceptProposedAction()

    def dropEvent(self, event):
        """아이템이 드롭되었을 때 실행되는 로직입니다."""
        mime_data = event.mimeData()
        if not mime_data.hasFormat('application/x-qabstractitemmodeldatalist'):
            return

        # QTreeWidget의 기본 MIME 데이터에서 UserRole 데이터를 추출합니다.
        encoded_data = mime_data.data('application/x-qabstractitemmodeldatalist')
        # 복잡한 디코딩 대신, QTreeWidget의 내부 드래그 정보를 활용하는 것이 더 안정적입니다.
        # 여기서는 임시로 드래그된 텍스트를 가져오는 방식을 사용합니다.
        # 실제로는 dropMimeData를 오버라이드하는 것이 더 좋습니다.
        
        # 임시 해결책: 드래그 소스 위젯에 접근할 수 없으므로,
        # 드롭된 아이템의 텍스트를 기반으로 정보를 재구성합니다.
        # 이는 한계가 있으며, 8장에서 데이터 모델 중심으로 개선될 것입니다.
        # 지금은 시각적인 기초를 다지는 데 집중합니다.
        
        # TODO: 8장에서 데이터 모델 기반으로 재설계 필요
        # 임시로 라벨을 추가하여 시각적 피드백만 제공합니다.
        temp_label = QLabel("New Step Dropped (Data will be linked later)")
        temp_label.setStyleSheet("background-color: white; border: 1px solid blue; padding: 10px; border-radius: 5px;")
        
        proxy_widget = self.scene.addWidget(temp_label)
        proxy_widget.setPos(10, self.y_pos_counter) 
        self.y_pos_counter += proxy_widget.boundingRect().height() + 10
        
        event.acceptProposedAction()
