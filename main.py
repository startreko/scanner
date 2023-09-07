import sys
import re
import time
import threading
from datetime import datetime

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import QMetaObject, Slot, QSharedMemory, QTimer, QCoreApplication
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QMessageBox
import keyboard
import tkinter as tk
from tkinter import messagebox

from xml_scanner import XMLScanner
from telnet_connector import TelnetConnector
from config_manager import ConfigManager
from database import Database


class ScannerMainWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Scanner")
        self.setWindowIcon(QIcon('icon.ico'))

        self.config_manager = ConfigManager('config.ini')
        self.config_manager.load_config()

        self.shared_memory = QSharedMemory("ScannerUniqueID")
        if self.shared_memory.attach():
            sys.exit(0)
        if not self.shared_memory.create(1):
            sys.exit(0)

        self.initialize_labels()

        self.xml_path = self.config_manager.get_config('CONFIG', 'xml_path')
        self.xml_scanner = XMLScanner(self.xml_path)

        self.db_path = self.config_manager.get_config('CONFIG', 'db_path')
        self.machine_name = self.config_manager.get_config('CONFIG', 'machine_name')

        self.application_active = True

        initial_db = Database(self.db_path, None, self.machine_name)

        server_address = self.config_manager.get_config('CONFIG', 'server_ip')
        server_port = int(self.config_manager.get_config('CONFIG', 'server_port'))

        self.telnet_connector = TelnetConnector(server_address, server_port)
        self.telnet_connector.connection_status_changed.connect(self.on_connection_status_changed)
        self.telnet_connector.response_received.connect(self.on_response_received)

        self.message_timer = QTimer()
        self.message_timer.timeout.connect(self.telnet_connector.send_and_receive)

        self.reconnect_timer = QTimer()
        self.reconnect_timer.timeout.connect(self.attempt_reconnect)

        self.scanned_code = ""
        self.previous_code = ""
        self.delayed_task = None
        self.code_pattern = re.compile(r'\d{7}-\d{6}-\d{7}')

        self.set_window_properties()
        self.start_keyboard_listener()
        QCoreApplication.instance().aboutToQuit.connect(self.cleanup)

    def initialize_labels(self):
        self.layout = QtWidgets.QHBoxLayout(self)
        self.setLayout(self.layout)

        self.num_label = QtWidgets.QLabel("Scan code")
        self.fabric_label = QtWidgets.QLabel()
        self.length_label = QtWidgets.QLabel()
        self.uv_label = QtWidgets.QLabel()

        labels = [self.num_label, self.fabric_label, self.length_label, self.uv_label]

        for label in labels:
            label.setStyleSheet("color: #FF6600; font-size: 20px; padding: 1px;")
            label.setFont(QtGui.QFont("Arial", 20, QtGui.QFont.Bold))
            self.uv_label.setStyleSheet("color: #000000; font-size: 20px; padding: 1px;")
            self.layout.addWidget(label)

    def set_window_properties(self):
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setWindowOpacity(1)
        self.setGeometry(50, 105, 250, 50)

    def cleanup(self):
        self.application_active = False
        self.telnet_connector.send_and_receive(message="!ST")
        self.telnet_connector.send_and_receive(message="!NC")
        time.sleep(2)
        self.telnet_connector.disconnect()

    def start_keyboard_listener(self):
        keyboard.on_press(self.on_key_press)

    def on_key_press(self, event):
        key = event.name
        self.scanned_code += key
        match = self.code_pattern.search(self.scanned_code)
        if match:
            self.process_scanned_code(match.group(0))

    def process_scanned_code(self, code):
        order_length, order_fabric, order_uv = self.xml_scanner.scan_xml(code)
        self.update_labels(code, order_length, order_fabric, order_uv)

        if self.delayed_task and self.delayed_task.is_alive():
            self.delayed_task.cancel()

        db = Database(self.db_path, code, self.machine_name)
        scan_info = db.check_if_scanned(code)

        if scan_info is not None:
            scan_time, machine = scan_info
            time_diff = datetime.now() - datetime.strptime(scan_time, "%Y-%m-%d %H:%M:%S")
            days, remainder = divmod(time_diff.total_seconds(), 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, _ = divmod(remainder, 60)

            tkinter_message = f"This order was already scanned {int(days)} days {int(hours)} hours {int(minutes)} minutes ago on machine {machine}. Do you want to scan again?"
            root = tk.Tk()
            root.withdraw()
            result = messagebox.askyesno('Warning', tkinter_message, parent=root)

            if not result:
                return
        self.telnet_connector.send_and_receive(message=f"{code}")
        self.delayed_task = threading.Timer(3, self.telnet_connector.send_and_receive, ["!ST"])
        self.delayed_task.start()

    def update_labels(self, code, length, fabric, uv):
        self.num_label.setText(code)
        self.length_label.setText(length)
        self.fabric_label.setText(fabric)
        self.uv_label.setText(uv)

    @Slot(str)
    def on_connection_status_changed(self, status):
        if status == "disconnected":
            self.reconnect_timer.start(5000)
        elif status == "connected":
            self.reconnect_timer.stop()
        elif status == "connecting":
            pass

    @Slot(str)
    def on_response_received(self, response):
        pass

    def attempt_reconnect(self):
        self.telnet_connector.send_and_receive(message="!NC")


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = ScannerMainWindow()
    window.show()
    sys.exit(app.exec_())
