import sys
import json
import csv
import datetime
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, QMessageBox, QFileDialog
from PyQt5.QtGui import QPainter, QPen, QColor
from PyQt5.QtCore import Qt, QTimer

CONFIG_FILE = "config.json"  # File to store saved window/button configuration

class TreadmillInterface(QWidget):
    def __init__(self):
        super().__init__()

        # Load configuration if available
        self.load_config()

        # COP position
        self.cop_x = 0  # X axis center (-0.5 to +0.5)
        self.cop_y = 0  # Y axis center (0 to 1.53)

        # Recording management
        self.is_recording = False
        self.data_log = []

        # Buttons
        self.record_button = QPushButton("Record")
        self.start_button = QPushButton("START")
        self.stop_button = QPushButton("STOP")

        # Button styles
        self.record_button.setStyleSheet("background-color: lightgray; font-size: 14px; padding: 5px;")
        self.start_button.setStyleSheet("background-color: lightgreen; font-size: 16px; padding: 5px;")
        self.stop_button.setStyleSheet("background-color: lightcoral; font-size: 16px; padding: 5px;")

        # Speed label
        self.speed_label = QLabel("Speed: 0.00 m/s")
        self.speed_label.setAlignment(Qt.AlignCenter)
        self.speed_label.setStyleSheet(
            "font-size: 16px; background-color: lightblue; border-radius: 5px; padding: 5px;"
        )

        # COP X and Y labels
        self.cop_x_label = QLabel("COP X: 0.00 m")
        self.cop_x_label.setAlignment(Qt.AlignCenter)
        self.cop_x_label.setStyleSheet(
            "font-size: 16px; background-color: lightyellow; border-radius: 5px; padding: 5px;"
        )

        self.cop_y_label = QLabel("COP Y: 0.00 m")
        self.cop_y_label.setAlignment(Qt.AlignCenter)
        self.cop_y_label.setStyleSheet(
            "font-size: 16px; background-color: lightyellow; border-radius: 5px; padding: 5px;"
        )

        # Layouts
        layout = QVBoxLayout()

        top_layout = QHBoxLayout()
        top_layout.addWidget(self.record_button)
        top_layout.addStretch()
        layout.addLayout(top_layout)

        start_layout = QHBoxLayout()
        start_layout.addStretch()
        start_layout.addWidget(self.start_button)
        start_layout.addStretch()
        layout.addLayout(start_layout)

        speed_layout = QHBoxLayout()
        speed_layout.addStretch()
        speed_layout.addWidget(self.speed_label)
        speed_layout.addStretch()
        layout.addLayout(speed_layout)

        layout.addStretch()

        # COP labels layout below treadmill
        cop_layout = QHBoxLayout()
        cop_layout.addStretch()
        cop_layout.addWidget(self.cop_x_label)
        cop_layout.addWidget(self.cop_y_label)
        cop_layout.addStretch()
        layout.addLayout(cop_layout)

        stop_layout = QHBoxLayout()
        stop_layout.addStretch()
        stop_layout.addWidget(self.stop_button)
        stop_layout.addStretch()
        layout.addLayout(stop_layout)

        self.setLayout(layout)

        # Restore button positions if available
        self.restore_positions()
        self.record_button.clicked.connect(self.toggle_recording)

        self.show()

    def paintEvent(self, event):
        """Draws the treadmill, lines, and COP with optimal and limit zones."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()

        treadmill_top = int(height * 0.25)
        treadmill_bottom = int(height * 0.75)
        treadmill_left = int(width * 0.2)
        treadmill_right = int(width * 0.8)
        treadmill_center_x = (treadmill_left + treadmill_right) // 2
        treadmill_height = treadmill_bottom - treadmill_top

        # Draw treadmill
        painter.setBrush(QColor(200, 200, 200))
        painter.drawRect(treadmill_left, treadmill_top, treadmill_right - treadmill_left, treadmill_height)

        # Horizontal medial line at y = 0.7
        pen_blue = QPen(QColor(100, 100, 255), 2, Qt.SolidLine)
        painter.setPen(pen_blue)
        medial_y = treadmill_top + treadmill_height - int(0.7 * treadmill_height / 1.53)
        painter.drawLine(treadmill_left, medial_y, treadmill_right, medial_y)

        # Optimal zone in green (y from 0.5 to 0.9)
        painter.setBrush(QColor(100, 200, 100, 100))  # Transparent green
        optimal_top = treadmill_top + treadmill_height - int(0.9 * treadmill_height / 1.53)
        optimal_bottom = treadmill_top + treadmill_height - int(0.5 * treadmill_height / 1.53)
        painter.drawRect(treadmill_left, optimal_top, treadmill_right - treadmill_left, optimal_bottom - optimal_top)

        # Front and back limit lines
        pen_red = QPen(QColor(255, 100, 100), 2, Qt.DashLine)
        painter.setPen(pen_red)

        # Front limit (y = 1.2)
        limit_front = treadmill_top + treadmill_height - int(1.2 * treadmill_height / 1.53)
        painter.drawLine(treadmill_left, limit_front, treadmill_right, limit_front)

        # Back limit (y = 0.2)
        limit_back = treadmill_top + treadmill_height - int(0.2 * treadmill_height / 1.53)
        painter.drawLine(treadmill_left, limit_back, treadmill_right, limit_back)

        # Vertical center line (x = 0)
        pen_black = QPen(Qt.black, 2, Qt.SolidLine)
        painter.setPen(pen_black)
        painter.drawLine(treadmill_center_x, treadmill_top, treadmill_center_x, treadmill_bottom)

        # Draw COP
        x_pos = treadmill_center_x + int(self.cop_x * (treadmill_right - treadmill_left) / 2)
        y_pos = treadmill_top + treadmill_height - int(self.cop_y * treadmill_height / 1.53)

        painter.setBrush(QColor(0, 0, 0))
        painter.drawEllipse(x_pos - 5, y_pos - 5, 10, 10)

    def update_cop(self, cop_x, cop_y):
        """Update COP position and refresh display."""
        self.cop_x = max(-0.5, min(0.5, cop_x))
        self.cop_y = max(0, min(1.53, cop_y))
        self.update()

        self.cop_x_label.setText(f"COP X: {self.cop_x:.2f} m")
        self.cop_y_label.setText(f"COP Y: {self.cop_y:.2f} m")

    def log_data(self, step, treadmill_speed, treadmill_acceleration, cop_measured, cop_estimated):
        """Log one row of data."""
        if self.is_recording:
            self.data_log.append([step, treadmill_speed, treadmill_acceleration, cop_measured, cop_estimated])

    def closeEvent(self, event):
        """Save configuration before closing."""
        self.save_config()
        event.accept()

    def load_config(self):
        """Load configuration if it exists."""
        try:
            with open(CONFIG_FILE, "r") as file:
                config = json.load(file)
                self.resize(*config["window_size"])
                self.button_positions = config
        except FileNotFoundError:
            self.button_positions = None

    def save_config(self):
        """Save current window size and button positions."""
        config = {
            "window_size": [self.width(), self.height()],
            "record_button": [self.record_button.x(), self.record_button.y()],
            "start_button": [self.start_button.x(), self.start_button.y()],
            "stop_button": [self.stop_button.x(), self.stop_button.y()]
        }

        with open(CONFIG_FILE, "w") as file:
            json.dump(config, file)

    def restore_positions(self):
        """Restore button positions from config if available."""
        if hasattr(self, "button_positions") and self.button_positions:
            for button_name in ["record_button", "start_button", "stop_button"]:
                if button_name in self.button_positions and isinstance(self.button_positions[button_name], list) and len(self.button_positions[button_name]) == 2:
                    getattr(self, button_name).move(*self.button_positions[button_name])

    def toggle_recording(self):
        """Toggle data recording."""
        self.is_recording = not self.is_recording
        if not self.is_recording:
            self.auto_export_csv()

        if self.is_recording:
            self.record_button.setStyleSheet("background-color: red; font-size: 14px; padding: 5px;")
            self.record_button.setText("Recording...")
            self.data_log = []
        else:
            self.record_button.setStyleSheet("background-color: lightgray; font-size: 14px; padding: 5px;")
            self.record_button.setText("Record")

    def auto_export_csv(self):
        """Automatically export data to CSV after recording ends."""
        if not self.data_log:
            return

        timestamp = datetime.datetime.now().strftime("%Y_%m_%d")
        default_filename = f"acquisition_{timestamp}.csv"

        file_path, _ = QFileDialog.getSaveFileName(self, "Save CSV", default_filename, "CSV Files (*.csv)")

        if file_path:
            with open(file_path, "w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(["Treadmill_speed", "Treadmill_acceleration", "COP_measured", "COP_filtered"])
                writer.writerows([row[1:] for row in self.data_log])

            # Visual confirmation: Record button turns green for 3s
            self.record_button.setStyleSheet("background-color: green; font-size: 14px; padding: 5px;")
            QTimer.singleShot(3000, lambda: self.record_button.setStyleSheet(
                "background-color: lightgray; font-size: 14px; padding: 5px;"))

    def resizeEvent(self, event):
        """Save window size when resized."""
        self.save_config()
        super().resizeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    interface = TreadmillInterface()
    sys.exit(app.exec_())
