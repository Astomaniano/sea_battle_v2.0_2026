import json
import os


class ScoreManager:
    def __init__(self, path):
        self.path = path
        self.records = []
        self.load()

    @staticmethod
    def format_time(seconds):
        sec = max(0, int(seconds))
        return f"{sec // 60:02d}:{sec % 60:02d}"

    @staticmethod
    def _parse_seconds(value):
        if isinstance(value, int):
            return max(0, value)
        if isinstance(value, str):
            parts = value.split(":")
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                return int(parts[0]) * 60 + int(parts[1])
        return None

    def load(self):
        raw = []
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
            except (json.JSONDecodeError, OSError):
                raw = []

        normalized = []
        for rec in raw if isinstance(raw, list) else []:
            if not isinstance(rec, dict):
                continue
            name = str(rec.get("name", "")).strip()
            if not name:
                continue

            seconds = rec.get("seconds")
            if not isinstance(seconds, int):
                seconds = self._parse_seconds(rec.get("time"))
            if seconds is None:
                continue

            normalized.append(
                {
                    "name": name,
                    "seconds": int(seconds),
                    "time": self.format_time(seconds),
                }
            )

        normalized.sort(key=lambda r: r["seconds"])
        self.records = normalized[:10]

    def add_record(self, name, seconds):
        sec = max(0, int(seconds))
        self.records.append({"name": name, "seconds": sec, "time": self.format_time(sec)})
        self.records.sort(key=lambda r: r["seconds"])
        self.records = self.records[:10]
        self.save()

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.records, f, ensure_ascii=False, indent=2)
        except OSError:
            pass
