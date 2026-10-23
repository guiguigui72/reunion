import json
import os
import time
from pathlib import Path

DATA_DIR = Path(os.environ.get("REUNION_HOME", str(Path.home() / ".reunion")))
CONFIG_PATH = DATA_DIR / "config.json"
PERSONA_PATH = DATA_DIR / "persona.md"
AVATAR_PATH = DATA_DIR / "avatar.png"
CORRECTIONS_PATH = DATA_DIR / "corrections.jsonl"


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict:
    ensure_data_dir()
    if not CONFIG_PATH.exists():
        return {}

    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        # 配置损坏不该让应用启动即崩。
        # 保留坏文件供排查，降级为默认配置。
        broken = CONFIG_PATH.parent / f"{CONFIG_PATH.name}.corrupt-{int(time.time())}"
        CONFIG_PATH.replace(broken)
        return {}


def save_config(config: dict) -> None:
    ensure_data_dir()
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def is_configured() -> bool:
    """Return True if the user has completed initial setup."""
    config = load_config()
    return bool(config.get("api_key") and config.get("name") and config.get("persona"))
