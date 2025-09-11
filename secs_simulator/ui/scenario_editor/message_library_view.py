from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PySide6.QtCore import Qt, QMimeData, Signal
from PySide6.QtGui import QDrag
from typing import Dict, Any

class MessageLibraryView(QTreeWidget):
    """
    디바이스 타입별 메시지 라이브러리를 표시하고 드래그 앤 드롭 및 클릭 신호를 제공합니다.
    """
    # ✅ [9장 추가] 메시지 아이템 클릭 시 발생하는 신호 (수동 전송용)
    message_selected = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderLabel("Message Libraries")
        self.setDragEnabled(True)
        # ✅ [9장 추가] 아이템 클릭 시그널을 내부 슬롯에 연결
        self.itemClicked.connect(self._on_item_clicked)

    def populate(self, libraries: Dict[str, Any]):
        self.clear()
        for device_type, messages in libraries.items():
            type_item = QTreeWidgetItem(self, [device_type])
            if messages:
                for msg_id, msg_body in messages.items():
                    sf = f"S{msg_body.get('s', '?')}F{msg_body.get('f', '?')}"
                    msg_item = QTreeWidgetItem(type_item, [f"{msg_id} ({sf})"])
                    
                    msg_item.setData(0, Qt.ItemDataRole.UserRole, {
                        "device_type": device_type,
                        "message_id": msg_id,
                        "message": msg_body
                    })

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if not item or not item.parent():
            return

        drag_data = item.data(0, Qt.ItemDataRole.UserRole)
        if not drag_data:
            return

        mime_data = QMimeData()
        mime_data.setText(f"secs-message/{drag_data['device_type']}/{drag_data['message_id']}")
        
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec(supportedActions)

    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """메시지 아이템이 클릭되면 message_selected 신호를 발생시킵니다."""
        # 디바이스 타입 아이템(최상위)은 무시
        if not item or not item.parent():
            return

        message_data = item.data(0, Qt.ItemDataRole.UserRole)
        if message_data:
            self.message_selected.emit(message_data)
