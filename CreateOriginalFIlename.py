import sys
import json
import re
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QFormLayout, QWidget, QLabel, QLineEdit, QComboBox, 
                             QPushButton, QDateEdit, QCheckBox, QSpinBox, QMessageBox,
                             QScrollArea, QFrame)
from PyQt6.QtCore import Qt, QDate, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette, QIcon
from PyQt6.QtCore import QPropertyAnimation, QEasingCurve

FILENAME_CONFIG = {
    "default": {
        "segments": [
            {
                "name": "study",
                "label": "Study",
                "type": "combo",
                "options": ["BIO", "ENTRAIN", "U54SingleDose", "HealX", "Other"],
                "validation": r"^[A-Za-z0-9]+$",
                "error_message": "Study name must be alphanumeric"
            },
            {
                "name": "visit_number",
                "label": "Visit Number",
                "type": "spinbox",
                "validation": r"^\d+$",
                "error_message": "Visit number must be a positive integer"
            },
            {
                "name": "file_type",
                "label": "File Type",
                "type": "combo",
                "options": ["rest", "chirp", "SSCT", "RLEEG", "Talk", "Listen", "VDAudio", "VDNoAudio", "Other"],
                "validation": r"^[A-Za-z]+$",
                "error_message": "File type must be alphabetic"
            },
            {
                "name": "subject_id",
                "label": "Subject ID",
                "type": "text",
                "validation": r"^\d{5}$",
                "error_message": "Subject ID must be 5 digits"
            },
            {
                "name": "subject_initials",
                "label": "Subject Initials",
                "type": "text",
                "validation": r"^[A-Z]{2}$",
                "error_message": "Subject Initials must be 2 uppercase letters"
            },
            {
                "name": "date",
                "label": "Date",
                "type": "date",
                "validation": r"^\d{2}-\d{2}-\d{4}$",
                "error_message": "Date must be in MM-DD-YYYY format"
            }
        ],
        "optional_suffixes": [
            {
                "name": "babycap",
                "label": "Baby Cap",
                "type": "checkbox"
            },
            {
                "name": "speakers",
                "label": "Speakers",
                "type": "checkbox"
            }
        ]
    },
    "BIO": {
        "segments": [
            {
                "name": "study",
                "label": "Study",
                "type": "text",
                "default": "BIO",
                "editable": False
            },
            # ... other segments remain the same as default
        ],
        "optional_suffixes": [
            {
                "name": "babycap",
                "label": "Baby Cap",
                "type": "checkbox"
            }
        ]
    }
    # ... other presets can be added here
}

class FilenameGenerator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EEG Filename Generator")
        self.setGeometry(100, 100, 600, 800)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QLabel {
                font-size: 14px;
                color: #333;
            }
            QComboBox, QLineEdit, QDateEdit, QSpinBox {
                font-size: 14px;
                padding: 5px;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            QPushButton {
                font-size: 16px;
                padding: 10px;
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QCheckBox {
                font-size: 14px;
            }
        """)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(FILENAME_CONFIG.keys())
        self.preset_combo.currentTextChanged.connect(self.load_preset)
        self.layout.addWidget(QLabel("Select Preset:"))
        self.layout.addWidget(self.preset_combo)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.form_layout = QFormLayout(self.scroll_content)
        self.scroll_area.setWidget(self.scroll_content)
        self.layout.addWidget(self.scroll_area)
        
        self.inputs = {}
        self.load_preset("default")
        
        self.result_frame = QFrame()
        self.result_frame.setStyleSheet("""
            QFrame {
                background-color: #e0e0e0;
                border-radius: 8px;
                padding: 10px;
                margin-top: 10px;
                margin-bottom: 10px;
            }
        """)
        self.result_layout = QHBoxLayout(self.result_frame)
        self.result_label = QLabel()
        self.result_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        self.result_layout.addWidget(self.result_label)
        
        self.copy_button = QPushButton()
        self.copy_button.setIcon(QIcon.fromTheme("edit-copy"))
        self.copy_button.setToolTip("Copy to Clipboard")
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        self.copy_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
        """)
        self.result_layout.addWidget(self.copy_button)
        
        self.layout.addWidget(self.result_frame)
        self.result_frame.hide()
        
        self.generate_button = QPushButton("Generate Filename")
        self.generate_button.clicked.connect(self.generate_filename)
        self.layout.addWidget(self.generate_button)

    def load_preset(self, preset_name):
        self.clear_form()
        preset = FILENAME_CONFIG[preset_name]
        
        for segment in preset["segments"]:
            widget = self.create_widget(segment)
            self.form_layout.addRow(segment["label"], widget)
            self.inputs[segment["name"]] = widget
        
        for suffix in preset["optional_suffixes"]:
            widget = QCheckBox(suffix["label"])
            self.form_layout.addRow("", widget)
            self.inputs[suffix["name"]] = widget

    def create_widget(self, segment):
        if segment["type"] == "text":
            widget = QLineEdit()
            if "default" in segment:
                widget.setText(segment["default"])
            if "editable" in segment and not segment["editable"]:
                widget.setReadOnly(True)
            widget.textChanged.connect(lambda: self.validate_field(segment["name"]))
        elif segment["type"] == "combo":
            widget = QComboBox()
            widget.addItems(segment["options"])
            widget.currentTextChanged.connect(lambda: self.validate_field(segment["name"]))
        elif segment["type"] == "date":
            widget = QDateEdit()
            widget.setCalendarPopup(True)
            widget.setDate(QDate.currentDate())
            widget.dateChanged.connect(lambda: self.validate_field(segment["name"]))
        elif segment["type"] == "spinbox":
            widget = QSpinBox()
            widget.setMinimum(1)
            widget.valueChanged.connect(lambda: self.validate_field(segment["name"]))
        return widget

    def clear_form(self):
        while self.form_layout.rowCount() > 0:
            self.form_layout.removeRow(0)
        self.inputs.clear()

    def validate_field(self, field_name):
        preset = FILENAME_CONFIG[self.preset_combo.currentText()]
        segment = next((s for s in preset["segments"] if s["name"] == field_name), None)
        if segment:
            value = self.get_input_value(field_name)
            if re.match(segment["validation"], value):
                self.inputs[field_name].setStyleSheet("border: 1px solid green;")
            else:
                self.inputs[field_name].setStyleSheet("border: 1px solid red;")
        self.update_preview()

    def update_preview(self):
        try:
            filename_parts = []
            preset = FILENAME_CONFIG[self.preset_combo.currentText()]
            
            for segment in preset["segments"]:
                value = self.get_input_value(segment["name"])
                filename_parts.append(value)
            
            filename = "_".join(filename_parts)
            
            for suffix in preset["optional_suffixes"]:
                if self.inputs[suffix["name"]].isChecked():
                    filename += f"_{suffix['name']}"
            
            self.result_label.setText(filename)
            self.result_frame.show()
        except Exception as e:
            self.result_label.setText("Invalid input")

    def generate_filename(self):
        try:
            filename_parts = []
            preset = FILENAME_CONFIG[self.preset_combo.currentText()]
            
            for segment in preset["segments"]:
                value = self.get_input_value(segment["name"])
                if not re.match(segment["validation"], value):
                    raise ValueError(segment["error_message"])
                filename_parts.append(value)
            
            filename = "_".join(filename_parts)
            
            for suffix in preset["optional_suffixes"]:
                if self.inputs[suffix["name"]].isChecked():
                    filename += f"_{suffix['name']}"
            
            self.result_label.setText(filename)
            self.result_frame.show()
            self.animate_result_frame()
        except ValueError as e:
            QMessageBox.warning(self, "Validation Error", str(e))

    def get_input_value(self, name):
        widget = self.inputs[name]
        if isinstance(widget, QLineEdit):
            return widget.text()
        elif isinstance(widget, QComboBox):
            return widget.currentText()
        elif isinstance(widget, QDateEdit):
            return widget.date().toString("MM-dd-yyyy")
        elif isinstance(widget, QSpinBox):
            return str(widget.value())
        return ""

    def copy_to_clipboard(self):
        filename = self.result_label.text()
        QApplication.clipboard().setText(filename)
        self.copy_button.setIcon(QIcon.fromTheme("emblem-default"))
        QTimer.singleShot(2000, lambda: self.copy_button.setIcon(QIcon.fromTheme("edit-copy")))

    def animate_result_frame(self):
        animation = QPropertyAnimation(self.result_frame, b"geometry")
        animation.setDuration(300)
        animation.setStartValue(self.result_frame.geometry().adjusted(0, 50, 0, 50))
        animation.setEndValue(self.result_frame.geometry())
        animation.setEasingCurve(QEasingCurve.Type.OutBack)
        animation.start()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FilenameGenerator()
    window.show()
    sys.exit(app.exec())