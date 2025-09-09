from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PySide6.QtCore import Qt
from typing import Dict, Any

class MessageLibraryView(QTreeWidget):
    """디바이스 타입별로 메시지 라이브러리를 보여주는 트리 뷰입니다."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabel("Message Libraries")
        self.setDragEnabled(True)  # 드래그 기능 활성화

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
                    drag_data_text = f"secs-message/{device_type}/{msg_id}"
                    msg_item.setData(0, Qt.ItemDataRole.UserRole, drag_data_text)

    def startDrag(self, supportedActions):
        """Qt의 내장 드래그 기능을 사용하여 선택된 아이템의 데이터를 전달합니다."""
        item = self.currentItem()
        if not item or not item.parent():
            return
        
        drag_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not drag_data:
            return

        # QTreeWidget의 내장 드래그 앤 드롭 기능을 활용합니다.
        # mimeData()를 직접 설정할 필요 없이, UserRole에 저장된 데이터를 사용합니다.
        super().startDrag(supportedActions)
