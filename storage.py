import json
import os
import logging
from config import Config

class Storage:
    def __init__(self):
        self.file_path = Config.DB_FILE
        self._data = {}
        self._load()

    def _load(self):
        if os.path.exists(self.file_path):
            try:
                with open(self.file_path, 'r') as f:
                    self._data = json.load(f)
            except Exception:
                self._data = {}

    def _save(self):
        try:
            with open(self.file_path, 'w') as f:
                json.dump(self._data, f)
        except Exception:
            pass

    def set_watermark(self, user_id: int, text: str):
        key = str(user_id)
        if key not in self._data:
            self._data[key] = {}
        self._data[key]["text"] = text
        self._save()

    def set_color(self, user_id: int, color: str):
        key = str(user_id)
        if key not in self._data:
            self._data[key] = {}
        self._data[key]["color"] = color
        self._save()

    def get_user_data(self, user_id: int) -> dict:
        key = str(user_id)
        if key not in self._data:
            self._data[key] = {
                "text": Config.DEFAULT_WATERMARK,
                "color": "white"  # Default color
            }
            self._save()
        return self._data[key]

db = Storage()
