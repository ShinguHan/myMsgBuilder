from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PySide6.QtCore import Qt, QMimeData
from PySide6.QtGui import QDrag
from typing import Dict, Any

class MessageLibraryView(QTreeWidget):
    """
    디바이스 타입별 메시지 라이브러리를 표시하고 드래그 기능을 제공하는 위젯입니다.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabel("Message Libraries")
        self.setDragEnabled(True) # 드래그 기능 활성화

    def populate(self, libraries: Dict[str, Any]):
        """라이브러리 데이터로 트리 뷰를 채웁니다."""
        self.clear()
        for device_type, messages in libraries.items():
            type_item = QTreeWidgetItem(self, [device_type])
            if messages:
                for msg_id, msg_body in messages.items():
                    sf = f"S{msg_body.get('s', '?')}F{msg_body.get('f', '?')}"
                    msg_item = QTreeWidgetItem(type_item, [f"{msg_id} ({sf})"])
                    
                    # 드래그 시 전달할 데이터를 아이템에 저장합니다.
                    # UserRole은 Qt의 아이템들이 사용자 정의 데이터를 저장하는 표준 방식입니다.
                    msg_item.setData(0, Qt.ItemDataRole.UserRole, {
                        "device_type": device_type,
                        "message_id": msg_id
                    })

    def startDrag(self, supportedActions):
        """드래그가 시작될 때, 우리가 정의한 형식으로 데이터를 설정합니다."""
        item = self.currentItem()
        # 최상위 아이템(디바이스 타입)은 드래그할 수 없도록 방지
        if not item or not item.parent():
            return

        drag_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not drag_data:
            return

        # 드롭 대상이 어떤 종류의 데이터인지 식별할 수 있도록
        # "secs-message/CV/S1F1_AreYouThere"와 같은 텍스트 형식으로 데이터를 인코딩합니다.
        mime_data = QMimeData()
        mime_data.setText(f"secs-message/{drag_data['device_type']}/{drag_data['message_id']}")
        
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        # 드래그 동작을 실행합니다.
        drag.exec(supportedActions)
