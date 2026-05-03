import json
import os
from pathlib import Path

DATA_DIR = Path.home() / ".reunion"
CONFIG_PATH = DATA_DIR / "config.json"
PERSONA_PATH = DATA_DIR / "persona.md"
AVATAR_PATH = DATA_DIR / "avatar.png"


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    ensure_data_dir()
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


def save_config(config: dict) -> None:
    ensure_data_dir()
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def is_configured() -> bool:
    """Return True if the user has completed initial setup."""
    config = load_config()
    return bool(config.get("api_key") and config.get("name") and config.get("persona"))
