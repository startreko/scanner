import sys
import re
import time
import threading
import os
from datetime import datetime
import tkinter as tk
from tkinter import messagebox
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import QMetaObject, Slot, QSharedMemory, QTimer, QCoreApplication
from PySide6.QtWidgets import QMessageBox
from PySide6.QtGui import QIcon
import keyboard
from xml_scanner import XMLScanner
from telnet_connector import TelnetConnector
from config_manager import ConfigManager
from database import Database

(self, parent=None):
        super().__init__(parent)
        self.order_UV_value = ""
        self.setWindowTitle("SKANER")
        self.layout = QtWidgets.QHBoxLayout(self)
        self.setLayout(self.layout)
        self.setWindowIcon(QIcon('PLACEHOLDER_PATH'))

        
        self.config_manager = ConfigManager('PLACEHOLDER_PATH')
        self.config_manager.load_config()

        self.shared_memory = QSharedMemory("SkanerID")
        if self.shared_memory.attach():
            print("Już uruchomiono jedną instancję programu. Wyłączam.")
            sys.exit(0)
        if not self.shared_memory.create(1):
            print("Nie można utworzyć współdzielonej pamięci.")
            sys.exit(0)

        self.barcode_label = QtWidgets.QLabel("Zeskanuj kod")
        self.fabric_label = QtWidgets.QLabel()
        self.length_label = QtWidgets.QLabel()
        self.uv_label = QtWidgets.QLabel()

        self.labels = [self.barcode_label, self.fabric_label, self.length_label, self.uv_label]

        for label in self.labels:
            label.setStyleSheet("color: 
            label.setFont(QtGui.QFont("Arial", 20, QtGui.QFont.Bold))
            self.uv_label.setStyleSheet("color: 
            self.layout.addWidget(label)

        xml_path = self.config_manager.get_config('CONFIG', 'xml_path')  
        self.xml_scanner = XMLScanner(xml_path)

        self.db_path = self.config_manager.get_config('CONFIG', 'db_path')
        self.cutter_name = self.config_manager.get_config('CONFIG', 'cutter_name')

        self.app_active = True

        
        initial_db = Database(self.db_path, None, self.cutter_name)

        
        clean_mode = self.config_manager.get_config('CONFIG', 'clean_mode')
        if clean_mode == 'y':
            db = Database(self.db_path, None, self.cutter_name)
            db.remove_old_entries(21)

        server_address = self.config_manager.get_config('CONFIG', 'server_ip')  
        server_port = int(self.config_manager.get_config('CONFIG', 'server_port'))  

        self.telnet_connector = TelnetConnector(server_address, int(server_port))
        self.telnet_connector.connection_status_changed.connect(self.handle_connection_status_changed)
        self.telnet_connector.response_received.connect(self.handle_response_received)

        
        self.message_timer = QTimer()
        self.message_timer.timeout.connect(self.telnet_connector.send_and_receive)

        
        self.reconnect_timer = QTimer()
        self.reconnect_timer.timeout.connect(self.attempt_reconnect)


        self.code = ""
        self.prev_code = ""
        self.delayed_task = None
        self.code_regex = re.compile(r'\d{7}-\d{6}-\d{7}')

        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setWindowOpacity(1)

        self.setGeometry(50, 105, 250, 50)

        self.start_keyboard_listener()

        
        app.aboutToQuit.connect(self.cleanup)

    def contextMenuEvent(self, event):
        """ Obsługa menu kontekstowego. """
        contextMenu = QtWidgets.QMenu(self)

        uvAct = contextMenu.addAction("UV")
        uvAct.triggered.connect(lambda: [setattr(self, "order_UV_value", "UV"), self.handle_uv_selection()])

        noUvAct = contextMenu.addAction("brak UV")
        noUvAct.triggered.connect(lambda: [setattr(self, "order_UV_value", ""), self.handle_uv_selection()])

        logAct = contextMenu.addAction("LOG")
        logAct.triggered.connect(lambda: [self.create_log_file("Custom log entry")])

        exitAct = contextMenu.addAction("Zamknij aplikację")
        exitAct.triggered.connect(self.close_application)

        contextMenu.exec(event.globalPos())

    def handle_uv_selection(self):
        """ Obsługa wyboru UV w menu kontekstowym. """
        if self.order_UV_value == "UV":
            self.uv_label.setText("UV")
            self.telnet_connector.connect_to_server()
        else:
            self.uv_label.setText("")
            self.telnet_connector.send_and_receive(message="!ST")
            time.sleep(1)
            self.telnet_connector.send_and_receive(message="!NC")
            time.sleep(1)
            self.telnet_connector.disconnect_from_server()

    def close_application(self):
        """ Metoda do zamykania aplikacji. """
        self.close()


    def create_log_file(self, response):
        log_filename = "log.txt"
        mode = "a" if os.path.exists(log_filename) else "w"

        with open(log_filename, mode) as log_file:
            current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"{current_datetime}: {response}\n"
            log_file.write(log_entry)

    def cleanup(self):
        self.app_active = False
        print("Aplikacja jest zamykana.")
        self.telnet_connector.send_and_receive(message="!ST")
        time.sleep(1)
        self.telnet_connector.send_and_receive(message="!NC")
        time.sleep(1)
        self.telnet_connector.disconnect_from_server()

    def start_keyboard_listener(self):
        keyboard.on_press(self.handle_key_press)

    def handle_key_press(self, event):
        key = event.name
        self.code += key
        match = self.code_regex.search(self.code)
        if match:
            code = match.group(0)
            order_length, order_fabric, order_UV_value = self.xml_scanner.scan_xml(code)
            self.update_labels(code, order_length, order_fabric, order_UV_value)

            
            if self.delayed_task and self.delayed_task.is_alive():
                self.delayed_task.cancel()

            db = Database(self.db_path, code, self.cutter_name)
            scan_info = db.check_if_scanned(code)

            self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
            self.show()  
            self.repaint() 

            if scan_info is not None:
                scan_time, machine = scan_info
                scan_time = datetime.strptime(scan_time, "%Y-%m-%d %H:%M:%S")
                time_diff = datetime.now() - scan_time
                days = time_diff.days
                hours, remainder = divmod(time_diff.seconds, 3600)
                minutes, _ = divmod(remainder, 60)
                self.show_message(
                    f"UWAGA\n{code} zeskanowany\n{days} dni, {hours} godzin i {minutes} minut temu\nCutter: {machine}")
            else:
                
                self.delayed_task = threading.Timer(30.0, self.save_to_database, [code])
                self.delayed_task.start()

            self.code = ""
            self.debug_print(code)

            if order_UV_value == "UV":
                self.telnet_connector.connect_to_server()
            else:
                self.telnet_connector.send_and_receive(message="!ST")
                time.sleep(1)
                self.telnet_connector.send_and_receive(message="!NC")
                time.sleep(1)
                self.telnet_connector.disconnect_from_server()

    def save_to_database(self, code):
        if not self.app_active:
            return
        
        db = Database(self.db_path, code, self.cutter_name)
        db.create_or_update_database()

    def show_message(self, message):
        print(message)
        root = tk.Tk()
        root.withdraw()  

        top = tk.Toplevel(root)
        top.withdraw()  
        top.attributes("-topmost", True)  

        messagebox.showerror("Informacja", message, parent=top)
        top.destroy()  
        root.destroy()  

    def debug_print(self, code):
        print("Odnaleziony kod:", code)

    @Slot(bool)
    def handle_connection_status_changed(self, connected):
        if connected:
            print("Connected to the server, sending message...")
            self.reconnect_timer.stop()  
            self.message_timer.start(3000)  
        else:
            print("Disconnected from the server, setting UV label color to black...")
            self.uv_label.setStyleSheet("color: 
            
            if self.uv_label.text() == "UV":
                self.message_timer.stop()  
                self.reconnect_timer.start(5000)  
            else:
                self.message_timer.stop()  

    @Slot()
    def attempt_reconnect(self):
        if not self.telnet_connector.connected:
            print("Attempting to reconnect to the server...")
            self.telnet_connector.connect_to_server()

    @Slot(str)
    def handle_response_received(self, response):
        response = response.strip()  
        print(f"Handling response: {repr(response)}")
        

        if response in ["^0=RS1	1	0	0	190	0",
                        "^0=RS2	1	0	0	190	0",
                        "^0=RS3	1	0	0	190	0",
                        "^0=RS1	1	0	0	191	0",
                        "^0=RS2	1	0	0	191	0",
                        "^0=RS3	1	0	0	191	0"]:
            print("Drukarka wylaczona.")
            self.uv_label.setStyleSheet("color: 
            self.telnet_connector.send_and_receive(message="!PO")
            
            

        elif response in ["^0=RS1	2	0	0	190	0",
                          "^0=RS2	2	0	0	190	0",
                          "^0=RS3	2	0	0	190	0",
                          "^0=RS1	2	0	0	191	0",
                          "^0=RS2	2	0	0	191	0",
                          "^0=RS3	2	0	0	191	0"]:
            print("Wlaczanie.")
            self.uv_label.setStyleSheet("color: 
            

        elif response in ["^0=RS1	4	0	0	190	0",
                          "^0=RS2	4	0	0	190	0",
                          "^0=RS3	4	0	0	190	0",
                          "^0=RS1	4	0	0	191	0",
                          "^0=RS2	4	0	0	191	0",
                          "^0=RS3	4	0	0	191	0"]:
            print("Otwieranie dyszy")
            self.uv_label.setStyleSheet("color: 
            self.telnet_connector.send_and_receive(message="!NO")
            
            

        elif response in ["^0=RS1	5	0	0	190	0",
                          "^0=RS2	5	0	0	190	0",
                          "^0=RS3	5	0	0	190	0",
                          "^0=RS1	5	0	0	191	0",
                          "^0=RS2	5	0	0	191	0",
                          "^0=RS3	5	0	0	191	0"]:
            print("Dysza otwarta")
            self.uv_label.setStyleSheet("color: 
            self.telnet_connector.send_and_receive(message="!GO")
            
            

        elif response in ["^0=RS1	6	0	0	190	0",
                          "^0=RS2	6	0	0	190	0",
                          "^0=RS3	6	0	0	190	0",
                          "^0=RS1	6	0	0	191	0",
                          "^0=RS2	6	0	0	191	0",
                          "^0=RS3	6	0	0	191	0"]:
            print("Gotowa do druku")
            self.uv_label.setStyleSheet("color: 
            


        elif response in ["^0=RS4	4	PLACEHOLDER_VALUE	0	191	0", "^0=RS3	4	PLACEHOLDER_VALUE	0	191	0",
                          "^0=RS4	4	PLACEHOLDER_VALUE	0	190	0", "^0=RS3	4	PLACEHOLDER_VALUE	0	190	0"]:
            print("Funkcja oszczedzania solventu. Wlaczanie")
            self.uv_label.setStyleSheet("color: 
            self.telnet_connector.send_and_receive(message="!EQ")
            

        else:
            print("Unknown response, setting UV label color to blue.")
            self.uv_label.setStyleSheet("color: 

    def update_labels(self, code, order_length, order_fabric, order_UV_value):
        self.barcode_label.setText(code)
        self.fabric_label.setText(order_fabric)
        self.length_label.setText(order_length)
        self.uv_label.setText(order_UV_value)
        QCoreApplication.processEvents()

    def mousePressEvent(self, event):
        self.old_pos = event.globalPosition()

    def mouseMoveEvent(self, event):
        delta = event.globalPosition() - self.old_pos
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.old_pos = event.globalPosition()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())
