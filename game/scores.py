import os
import json


class ScoreManager:
    def __init__(self, path):
        self.path = path
        self.records = []
        self.load()

    def load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    self.records = json.load(f)
            except (json.JSONDecodeError, OSError):
                self.records = []
        else:
            self.records = []

    def add_record(self, name, seconds):
        self.records.append({"name": name, "time": seconds})
        self.records.sort(key=lambda r: r["time"])
        self.records = self.records[:10]
        self.save()

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.records, f, ensure_ascii=False, indent=2)
        except OSError:
            pass
