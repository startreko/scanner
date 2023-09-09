import sqlite3
from datetime import datetime, timedelta
import os

class Database:
    def __init__(self, file_path, scanned_code, machine):
        self.file_path = file_path
        self.scanned_code = scanned_code
        self.machine = machine


        conn = sqlite3.connect(self.file_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Scans(
                code TEXT,
                machine TEXT,
                date_time TEXT
            )
        """)


    def create_or_update_database(self):
        
        conn = sqlite3.connect(self.file_path)
        cursor = conn.cursor()

        date_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO Scans(code, machine, date_time) VALUES(?,?,?)
        """, (self.scanned_code, self.machine, date_time))

        conn.commit()
        conn.close()

    def check_if_scanned(self, code):
        
        conn = sqlite3.connect(self.file_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT date_time, machine FROM Scans WHERE code = ?
        """, (code,))

        result = cursor.fetchone()
        conn.close()

        return result

    def remove_old_entries(self, days_old):
        
        conn = sqlite3.connect(self.file_path)
        cursor = conn.cursor()

        cutoff_date = (datetime.now() - timedelta(days=days_old)).strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            DELETE FROM Scans WHERE date_time < ?
        """, (cutoff_date,))

        conn.commit()
        conn.close()
