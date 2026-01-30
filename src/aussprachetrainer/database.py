import sqlite3
import os
from datetime import datetime
from typing import List, Dict

class HistoryManager:
    def __init__(self, db_path: str = None):
        if db_path is None:
            config_dir = os.path.expanduser("~/.local/share/aussprachetrainer")
            os.makedirs(config_dir, exist_ok=True)
            db_path = os.path.join(config_dir, "history.db")
        
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text TEXT NOT NULL,
                    ipa TEXT,
                    audio_path TEXT,
                    mode TEXT,
                    voice_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def add_entry(self, text: str, ipa: str, audio_path: str, mode: str, voice_id: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO history (text, ipa, audio_path, mode, voice_id) VALUES (?, ?, ?, ?, ?)",
                (text, ipa, audio_path, mode, voice_id)
            )
            conn.commit()

    def get_history(self, search_query: str = None) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if search_query:
                cursor = conn.execute(
                    "SELECT * FROM history WHERE text LIKE ? ORDER BY created_at DESC",
                    (f"%{search_query}%",)
                )
            else:
                cursor = conn.execute("SELECT * FROM history ORDER BY created_at DESC")
            
            return [dict(row) for row in cursor.fetchall()]

    def delete_entry(self, entry_id: int):
        # We might want to delete the audio file too, but let's stick to DB for now
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM history WHERE id = ?", (entry_id,))
            conn.commit()

    def clear_history(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM history")
            conn.commit()
