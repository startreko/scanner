import sqlite3
from datetime import datetime, timedelta

class Database:
    def __init__(self, file_path, scanned_code, machine_name):
        self.file_path = file_path
        self.scanned_code = scanned_code
        self.machine_name = machine_name

        conn = sqlite3.connect(self.file_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Scans(
                    code TEXT,
                    machine_name TEXT,
                    date_time TEXT
                )
            """)
        finally:
            conn.commit()
            conn.close()

    def create_or_update_database(self):
        conn = sqlite3.connect(self.file_path)
        cursor = conn.cursor()

        try:
            date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO Scans(code, machine_name, date_time) VALUES(?,?,?)
            """, (self.scanned_code, self.machine_name, date_time))
        finally:
            conn.commit()
            conn.close()

    def check_if_scanned(self, code):
        conn = sqlite3.connect(self.file_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT date_time, machine_name FROM Scans WHERE code = ?
            """, (code,))
            result = cursor.fetchone()
        finally:
            conn.close()

        return result

    def remove_old_entries(self, days_old):
        conn = sqlite3.connect(self.file_path)
        cursor = conn.cursor()

        try:
            cutoff_date = (datetime.now() - timedelta(days=days_old)).strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                DELETE FROM Scans WHERE date_time < ?
            """, (cutoff_date,))
        finally:
            conn.commit()
            conn.close()
