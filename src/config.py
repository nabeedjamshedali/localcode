"""
Config manager for localcode.
Stores settings in ~/.localcode/config.json
"""
import os
import json
from pathlib import Path

CONFIG_DIR  = Path.home() / '.localcode'
CONFIG_FILE = CONFIG_DIR / 'config.json'

DEFAULTS = {
    'model': None,           # Auto-detect best available
    'ollama_url': 'http://localhost:11434',
    'auto_confirm': False,
    'max_context_lines': 500,
    'theme': 'dark',
}


class Config:
    def __init__(self):
        self._data = {**DEFAULTS}
        self._load()

    def _load(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE) as f:
                    saved = json.load(f)
                    self._data.update(saved)
            except Exception:
                pass

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value):
        self._data[key] = value
        self._save()

    def _save(self):
        CONFIG_DIR.mkdir(exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self._data, f, indent=2)
