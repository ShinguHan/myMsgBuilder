import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QGraphicsView, 
                               QGraphicsScene, QGraphicsItem, QPushButton, 
                               QVBoxLayout, QWidget)
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QPainter, QTextDocument, QColor, QBrush, QPen

class ResizableItem(QGraphicsItem):
    """
    내부 텍스트 양에 따라 높이가 동적으로 변하는 커스텀 그래픽 아이템입니다.
    """
    def __init__(self, initial_text, parent=None):
        super().__init__(parent)
        self.text_content = initial_text
        self.width = 250
        self.height = 50 # 초기 높이
        
        # 생성 시점의 텍스트로 첫 높이를 계산합니다.
        self._calculate_height()

    def boundingRect(self) -> QRectF:
        """이 아이템이 차지하는 영역을 시스템에 알립니다."""
        return QRectF(0, 0, self.width, self.height)

    def _calculate_height(self):
        """
        현재 텍스트 내용에 기반하여 아이템의 정확한 높이를 계산합니다.
        사용자님의 _calculate_and_set_height 와 동일한 역할을 합니다.
        """
        doc = QTextDocument()
        # HTML과 CSS를 사용하여 텍스트 래핑 및 스타일링을 제어합니다.
        html = f"""
        <div style='width: {self.width - 10}px; 
                     word-wrap: break-word;
                     color: #E0E0E0;'>
        {self.text_content}
        </div>
        """
        doc.setHtml(html)
        doc.setTextWidth(self.width - 10)
        # 계산된 문서 높이에 패딩을 더해 최종 높이를 설정합니다.
        self.height = doc.size().height() + 10

    def paint(self, painter: QPainter, option, widget):
        """아이템을 화면에 그립니다."""
        rect = self.boundingRect()
        
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QBrush(QColor("#1E1E1E")))
        painter.setPen(QPen(QColor("#454545"), 1))
        painter.drawRoundedRect(rect, 8.0, 8.0)
        
        # 텍스트를 그리기 위한 QTextDocument를 다시 생성합니다.
        doc = QTextDocument()
        html = f"""
        <div style='width: {self.width - 10}px; 
                     word-wrap: break-word;
                     color: #E0E0E0;'>
        {self.text_content}
        </div>
        """
        doc.setHtml(html)
        doc.setTextWidth(self.width - 10)

        # 아이템 내부 (5,5) 위치에 텍스트를 그립니다.
        painter.translate(5, 5)
        doc.drawContents(painter)

    def update_text_and_resize(self, new_text: str):
        """
        [핵심 로직]
        외부에서 호출하여 텍스트를 갱신하고 아이템 크기를 조절하는 메서드입니다.
        사용자님의 update_visuals 와 동일한 역할을 합니다.
        """
        print("--- Update Process Started ---")
        
        # 1. 중요: 시스템에 아이템의 크기/모양이 곧 바뀔 것이라고 '미리' 공지합니다.
        # 이것이 없으면 시스템은 아이템의 크기가 그대로라고 가정하고 화면을 갱신합니다.
        print("Step 1: Calling prepareGeometryChange()")
        self.prepareGeometryChange()
        
        # 2. 아이템의 내부 데이터를 새로운 내용으로 업데이트합니다.
        print("Step 2: Updating internal data (text_content)")
        self.text_content = new_text
        
        # 3. 새로운 데이터에 맞춰 아이템의 높이를 다시 계산합니다.
        # 이 시점에서 self.height 멤버 변수의 값이 바뀝니다.
        print("Step 3: Recalculating height")
        self._calculate_height()
        
        # 4. 시스템에 아이템을 다시 그려달라고 요청합니다. 
        # 이 때 시스템은 prepareGeometryChange() 호출을 기억하고, 
        # 변경된 boundingRect()를 다시 조회하여 화면을 올바르게 갱신합니다.
        print("Step 4: Calling update() to trigger repaint")
        self.update()
        print("--- Update Process Finished ---\n")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Resizable QGraphicsItem Example")
        self.setGeometry(100, 100, 400, 300)

        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        self.view.setStyleSheet("background-color: #2D2D2D; border: none;")

        # 예제 아이템을 생성하고 씬에 추가합니다.
        self.item = ResizableItem("Click the button to add more text here.")
        self.scene.addItem(self.item)

        # 아이템의 텍스트를 변경할 버튼을 생성합니다.
        self.button = QPushButton("Add Text & Resize")
        self.button.clicked.connect(self.on_button_click)
        
        self.counter = 0

        # 레이아웃을 설정합니다.
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.addWidget(self.view)
        layout.addWidget(self.button)
        self.setCentralWidget(central_widget)

    def on_button_click(self):
        """버튼 클릭 시 아이템에 텍스트를 추가하고 리사이즈를 요청합니다."""
        self.counter += 1
        new_text = self.item.text_content + f"<br>Line {self.counter}: This new line should make the item taller."
        self.item.update_text_and_resize(new_text)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
