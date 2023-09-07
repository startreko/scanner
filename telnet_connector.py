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
        print('Attempting to connect to the server...')
        try:
            self.tn = telnetlib.Telnet(self.server_address, self.server_port)
            self.connected = True
            self.connection_status_changed.emit(True)
            print('Connected to the server.')
        except Exception as e:
            print(f'Failed to connect to the server: {e}')

    @Slot()
    def disconnect_from_server(self):
        print('Attempting to disconnect from the server...')
        if self.tn:
            self.tn.close()
            self.tn = None
            self.connected = False
            self.connection_status_changed.emit(False)
            print('Disconnected from the server.')

    @Slot()
    def send_and_receive(self, message="?RS"):
        if not self.connected:
            print('Not connected to the server.')
            return

        message = f'^0{message}\r'.encode('ascii')
        print(f'Sending message to the server: {message}')

        try:
            self.tn.write(message)
            time.sleep(0.5)  # Added delay
            full_response = self._read_response_from_server()
            if full_response:  # Emit signal only if response is not empty
                self.response_received.emit(full_response)
        except Exception as e:
            print(f'Failed to communicate with the server: {e}')
            self.connected = False
            self.connection_status_changed.emit(False)

    def _read_response_from_server(self):
        full_response = ""
        while True:
            try:
                part_of_response = self.tn.read_very_eager()
                if not part_of_response:
                    break
                full_response += part_of_response.decode()
            except EOFError:
                print("Telnet connection closed.")
                self.response_received.emit("not_ok")
                self.connect_to_server()  # Modified from 'reconnect_to_server' as it does not exist in this code
                return ""
        print(f'Received response from the server: {full_response}')
        return full_response

    def start(self):
        self.thread.started.connect(self.connect_to_server)
        self.thread.finished.connect(self.disconnect_from_server)
        self.moveToThread(self.thread)
        self.thread.start()

    def stop(self):
        if self.thread.isRunning():
            self.thread.quit()
            self.thread.wait()