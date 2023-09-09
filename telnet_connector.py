import telnetlib
import time
from PySide6.QtCore import QObject, Signal, Slot, QThread

class TelnetConnector(QObject):
    connection_status_changed = Signal(bool)
    response_received = Signal(str)

    def __init__(self, server_address, server_port):
        super().__init__()

        self.server_address = server_address
        self.server_port = server_port
        self.tn = None
        self.connected = False
        self.thread = QThread()
    @Slot()
    def connect_to_server(self):
        
        try:
            self.tn = telnetlib.Telnet(self.server_address, self.server_port)
            self.connected = True
            self.connection_status_changed.emit(True)
            
        except Exception as e:
            

    @Slot()
    def disconnect_from_server(self):
        
        if self.tn:
            self.tn.close()
            self.tn = None
            self.connected = False
            self.connection_status_changed.emit(False)
            

    @Slot()
    def send_and_receive(self, message="?RS"):
        if not self.connected:
            
            return

        message = '^0' + message + '\r'
        message = message.encode('ascii')
        

        try:
            self.tn.write(message)
            time.sleep(0.5)
            full_response = ""
            while True:
                try:
                    part_of_response = self.tn.read_very_eager()
                    if not part_of_response:
                        break
                    full_response += part_of_response.decode()
                except EOFError:
                    
                    self.response_received.emit("not_ok")
                    self.reconnect_to_server()
                    return
            
            if full_response:
                self.response_received.emit(full_response)
        except Exception as e:
            
            self.connected = False
            self.connection_status_changed.emit(False)

    def start(self):
        self.thread.started.connect(self.connect_to_server)
        self.thread.finished.connect(self.disconnect_from_server)
        self.moveToThread(self.thread)
        self.thread.start()

    def stop(self):
        if self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()
