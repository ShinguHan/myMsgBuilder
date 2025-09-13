from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, 
                               QComboBox, QDialogButtonBox, QSpinBox)
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

        # ✅ [추가] Active/Passive 모드 선택 콤보박스
        self.connection_mode_input = QComboBox()
        self.connection_mode_input.addItems(["Passive", "Active"])

        form_layout.addRow("Device ID:", self.id_input)
        form_layout.addRow("Type:", self.type_input)
        form_layout.addRow("Connection Mode:", self.connection_mode_input)
        form_layout.addRow("Host IP:", self.host_input)
        form_layout.addRow("Port:", self.port_input)

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
            "connection_mode": self.connection_mode_input.currentText()
        }
