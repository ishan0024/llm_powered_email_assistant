import sqlite3
from datetime import datetime

DB_FILE = "email_tracker.db"

class EmailTrackerDB:
    def __init__(self):
        self.conn = sqlite3.connect(DB_FILE)
        self._create_table()

    def _create_table(self):
        with self.conn:
            self.conn.execute('''
                CREATE TABLE IF NOT EXISTS processed_emails (
                    message_id TEXT PRIMARY KEY,
                    processed_timestamp TEXT,
                    email_subject TEXT,
                    email_sender TEXT,
                    moved_status INTEGER DEFAULT 0,
                    move_timestamp TEXT
                )
            ''')

    def is_processed(self, message_id):
        cursor = self.conn.execute(
            "SELECT 1 FROM processed_emails WHERE message_id = ?", (message_id,))
        return cursor.fetchone() is not None

    def mark_processed(self, message_id, email_subject, email_sender):
        with self.conn:
            self.conn.execute('''
                INSERT OR IGNORE INTO processed_emails 
                (message_id, processed_timestamp, email_subject, email_sender) 
                VALUES (?, ?, ?, ?)
            ''', (message_id, datetime.utcnow().isoformat(), email_subject, email_sender))

    def mark_moved(self, message_id):
        with self.conn:
            self.conn.execute('''
                UPDATE processed_emails
                SET moved_status = 1,
                    move_timestamp = ?
                WHERE message_id = ?
            ''', (datetime.utcnow().isoformat(), message_id))

    def get_unmoved_processed(self):
        cursor = self.conn.execute('''
            SELECT message_id, email_subject, email_sender, processed_timestamp 
            FROM processed_emails
            WHERE moved_status = 0
        ''')
        return cursor.fetchall()

    def close(self):
        self.conn.close()