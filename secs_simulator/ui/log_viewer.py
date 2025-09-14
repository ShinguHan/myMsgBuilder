# secs_simulator/ui/log_viewer.py

import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QLineEdit,
                               QHeaderView, QAbstractItemView, QComboBox, QHBoxLayout, QLabel)
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QColor, QBrush

class QtLogHandler(logging.Handler, QObject):
    """Python의 로그 레코드를 Qt 시그널로 보내는 커스텀 핸들러"""
    log_received = Signal(object)

    def __init__(self, parent=None):
        super().__init__()
        QObject.__init__(self, parent)
        self.setFormatter(logging.Formatter('%(asctime)s.%(msecs)03d | %(levelname)-7s | %(name)s: %(message)s', datefmt='%H:%M:%S'))

    def emit(self, record):
        """logging 모듈에 의해 호출되어 시그널을 발생시킵니다."""
        self.log_received.emit(record)

class LogViewer(QWidget):
    """로그 레코드를 테이블 형태로 보여주는 위젯"""
    LOG_LEVEL_COLORS = {
        logging.DEBUG: QColor("#AAAAAA"),
        logging.INFO: QColor("#E0E0E0"),
        logging.WARNING: QColor("#FFD700"), # 노란색으로 변경
        logging.ERROR: QColor("#FF3B30"),
        logging.CRITICAL: QColor("#FF3B30"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 0)
        layout.setSpacing(5)

        # 필터 컨트롤 추가
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Log Level:"))
        self.level_filter = QComboBox()
        self.level_filter.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.level_filter.setCurrentText("DEBUG")
        self.level_filter.currentIndexChanged.connect(self.apply_filter)
        filter_layout.addWidget(self.level_filter)
        filter_layout.addStretch()

        # ✅ [핵심 추가] 텍스트 필터
        filter_layout.addWidget(QLabel("Filter Text:"))
        self.text_filter_input = QLineEdit()
        self.text_filter_input.setPlaceholderText("Enter text to filter logs...")
        self.text_filter_input.textChanged.connect(self.apply_filter) # 텍스트 변경 시 바로 필터링
        filter_layout.addWidget(self.text_filter_input)

        layout.addLayout(filter_layout)

        # 로그를 표시할 테이블 위젯
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Timestamp", "Level", "Source", "Message"])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # Timestamp
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # Level
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents) # Source
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)         # Message

        layout.addWidget(self.table)
        self.apply_filter() # 초기 필터 적용

    @Slot(object)
    def add_log_record(self, record: logging.LogRecord):
        """핸들러로부터 받은 로그 레코드를 테이블에 추가하는 슬롯"""
        row_position = self.table.rowCount()
        self.table.insertRow(row_position)
        
        timestamp_str = self.sender().formatter.formatTime(record, datefmt='%H:%M:%S') + f".{int(record.msecs):03d}"

        # 테이블 아이템 생성
        timestamp_item = QTableWidgetItem(timestamp_str)
        level_item = QTableWidgetItem(record.levelname)
        source_item = QTableWidgetItem(record.name)
        message_item = QTableWidgetItem(record.getMessage())
        
        # 로그 레벨에 따라 색상 적용
        color = self.LOG_LEVEL_COLORS.get(record.levelno, QColor("#E0E0E0"))
        
        for i, item in enumerate([timestamp_item, level_item, source_item, message_item]):
            item.setForeground(QBrush(color))
            self.table.setItem(row_position, i, item)

        # 행 추가 후, 현재 필터 조건에 따라 바로 보이거나 숨겨지도록 설정
        self.apply_filter_to_row(row_position)

        # # 필터링 로직: 현재 필터 레벨에 맞지 않으면 행을 숨김
        # selected_level_str = self.level_filter.currentText()
        # selected_level_val = logging.getLevelName(selected_level_str)
        # if record.levelno < selected_level_val:
        #     self.table.setRowHidden(row_position, True)

        self.table.scrollToBottom()

    @Slot()
    def apply_filter(self):
        """테이블의 모든 행에 현재 필터 조건을 다시 적용합니다."""
        for row in range(self.table.rowCount()):
            self.apply_filter_to_row(row)

    def apply_filter_to_row(self, row: int):
        """특정 행에 현재 레벨 및 텍스트 필터 조건을 적용하여 보이거나 숨깁니다."""
        # 1. 레벨 필터 조건 확인
        level_item = self.table.item(row, 1)
        selected_level_str = self.level_filter.currentText()
        selected_level_val = logging.getLevelName(selected_level_str)
        record_level_val = logging.getLevelName(level_item.text())
        level_match = (record_level_val >= selected_level_val)

        # 2. 텍스트 필터 조건 확인
        text_filter = self.text_filter_input.text().lower()
        if not text_filter:
            text_match = True # 필터 텍스트가 없으면 항상 통과
        else:
            # 모든 컬럼의 텍스트를 확인하여 필터 텍스트가 포함되는지 검사
            text_match = any(
                text_filter in self.table.item(row, col).text().lower() 
                for col in range(self.table.columnCount())
            )

        # 3. 두 조건이 모두 참일 때만 행을 보이게 함
        self.table.setRowHidden(row, not (level_match and text_match))