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
        self._data[str(user_id)] = text
        self._save()

    def get_watermark(self, user_id: int) -> str:
        return self._data.get(str(user_id), Config.DEFAULT_WATERMARK)

db = Storage()
