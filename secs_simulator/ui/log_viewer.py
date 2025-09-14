# secs_simulator/ui/log_viewer.py

import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, 
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
        self.level_filter.setCurrentText("INFO")
        self.level_filter.currentIndexChanged.connect(self.apply_filter)
        filter_layout.addWidget(self.level_filter)
        filter_layout.addStretch()
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
        self.apply_filter(0) # 초기 필터 적용

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

        # 필터링 로직: 현재 필터 레벨에 맞지 않으면 행을 숨김
        selected_level_str = self.level_filter.currentText()
        selected_level_val = logging.getLevelName(selected_level_str)
        if record.levelno < selected_level_val:
            self.table.setRowHidden(row_position, True)

        self.table.scrollToBottom()

    def apply_filter(self, index):
        """콤보박스 선택에 따라 로그 필터를 적용하는 슬롯"""
        selected_level_str = self.level_filter.currentText()
        selected_level_val = logging.getLevelName(selected_level_str)

        for row in range(self.table.rowCount()):
            level_item = self.table.item(row, 1)
            if level_item:
                record_level_val = logging.getLevelName(level_item.text())
                is_visible = (record_level_val >= selected_level_val)
                self.table.setRowHidden(row, not is_visible)