# secs_simulator/ui/add_device_dialog.py

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, 
                               QComboBox, QDialogButtonBox, QSpinBox, QLabel)
from PySide6.QtCore import Qt

class AddDeviceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Device")

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.id_input = QLineEdit()
        self.type_input = QComboBox()
        self.type_input.addItems(["CV", "Stocker", "OverheadHoist", "Custom"])
        self.type_input.setEditable(True)
        self.host_input = QLineEdit("127.0.0.1")
        self.port_input = QSpinBox()
        self.port_input.setRange(1024, 65535)
        self.port_input.setValue(5000)
        self.connection_mode_input = QComboBox()
        self.connection_mode_input.addItems(["Passive", "Active"])

        # --- 타임아웃 입력 필드 추가 ---
        self.t3_input = QSpinBox()
        self.t3_input.setRange(1, 300)
        self.t3_input.setValue(10)
        self.t3_input.setSuffix(" sec")
        
        self.t5_input = QSpinBox()
        self.t5_input.setRange(1, 300)
        self.t5_input.setValue(10)
        self.t5_input.setSuffix(" sec")

        self.t6_input = QSpinBox()
        self.t6_input.setRange(1, 300)
        self.t6_input.setValue(5)
        self.t6_input.setSuffix(" sec")

        self.t7_input = QSpinBox()
        self.t7_input.setRange(1, 300)
        self.t7_input.setValue(10)
        self.t7_input.setSuffix(" sec")

        form_layout.addRow("Device ID:", self.id_input)
        form_layout.addRow("Type:", self.type_input)
        form_layout.addRow("Connection Mode:", self.connection_mode_input)
        form_layout.addRow("Host IP:", self.host_input)
        form_layout.addRow("Port:", self.port_input)
        
        # 구분선과 타임아웃 필드를 레이아웃에 추가
        form_layout.addRow(QLabel("<b>HSMS Timeouts</b>"))
        form_layout.addRow("T3 (Reply Timeout):", self.t3_input)
        form_layout.addRow("T5 (Connection Separation):", self.t5_input)
        form_layout.addRow("T6 (Control Transaction):", self.t6_input)
        form_layout.addRow("T7 (Not Selected):", self.t7_input)

        layout.addLayout(form_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_device_info(self):
        device_id = self.id_input.text().strip()
        if not device_id:
            return None
            
        return {
            "id": device_id,
            "type": self.type_input.currentText(),
            "host": self.host_input.text(),
            "port": self.port_input.value(),
            "connection_mode": self.connection_mode_input.currentText(),
            "t3": self.t3_input.value(),
            "t5": self.t5_input.value(),
            "t6": self.t6_input.value(),
            "t7": self.t7_input.value()
        }