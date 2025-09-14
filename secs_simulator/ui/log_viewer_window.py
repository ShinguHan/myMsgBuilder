from PySide6.QtWidgets import QMainWindow, QFileDialog, QToolBar, QApplication
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtCore import Qt

from .log_viewer import LogViewer

class LogViewerWindow(QMainWindow):
    """
    독립된 창으로 동작하는 로그 뷰어.
    저장, 복사, 초기화, 필터링 기능을 포함합니다.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SECS/HSMS Log Viewer")
        self.setGeometry(200, 200, 1000, 700)

        # 메인 위젯으로 LogViewer를 설정합니다.
        self.log_viewer = LogViewer(self)
        self.setCentralWidget(self.log_viewer)

        # 기능 버튼을 담을 툴바를 생성합니다.
        toolbar = QToolBar("Log Actions")
        self.addToolBar(toolbar)

        # 저장(Save) 액션
        save_action = QAction("Save Logs", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_logs)
        toolbar.addAction(save_action)

        # 복사(Copy) 액션
        copy_action = QAction("Copy Selection", self)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        copy_action.triggered.connect(self.copy_logs)
        toolbar.addAction(copy_action)
        
        # 초기화(Clear) 액션
        clear_action = QAction("Clear All Logs", self)
        clear_action.setShortcut("Ctrl+L")
        clear_action.triggered.connect(self.clear_logs)
        toolbar.addAction(clear_action)

    def save_logs(self):
        """현재 보이는 로그를 텍스트 파일로 저장합니다."""
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Log File", "", "Log Files (*.log);;Text Files (*.txt)")
        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                table = self.log_viewer.table
                header = [table.horizontalHeaderItem(i).text() for i in range(table.columnCount())]
                f.write('\t'.join(header) + '\n')

                for row in range(table.rowCount()):
                    if not table.isRowHidden(row):
                        row_data = [table.item(row, col).text() for col in range(table.columnCount())]
                        f.write('\t'.join(row_data) + '\n')
        except Exception as e:
            print(f"Error saving log file: {e}")

    def copy_logs(self):
        """테이블에서 선택된 행들을 클립보드에 복사합니다."""
        table = self.log_viewer.table
        selected_rows = sorted(list(set(index.row() for index in table.selectedIndexes())))
        if not selected_rows:
            return

        clipboard = QApplication.clipboard()
        copy_text = []
        for row in selected_rows:
            if not table.isRowHidden(row):
                row_data = [table.item(row, col).text() for col in range(table.columnCount())]
                copy_text.append('\t'.join(row_data))
        
        clipboard.setText('\n'.join(copy_text))

    def clear_logs(self):
        """로그 테이블의 모든 내용을 삭제합니다."""
        self.log_viewer.table.setRowCount(0)

    def closeEvent(self, event):
        """창을 닫을 때 실제 종료되는 대신 숨김 처리하여, 로그를 계속 수신할 수 있도록 합니다."""
        self.hide()
        event.ignore()