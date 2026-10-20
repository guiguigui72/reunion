import asyncio

from api import settings
from config import CONFIG_PATH, load_config, save_config


def _put(**fields):
    """直接调用 async 端点，避免引入 pytest-asyncio。"""
    return asyncio.run(settings.update_settings(settings.SettingsUpdate(**fields)))


def _fresh_config():
    save_config({
        "api_key": "sk-test",
        "name": "妈妈",
        "your_name": "小明",
        "relationship": "母子",
        "personality": "话少",
        "extra": "",
        "has_avatar": True,
        "last_seen": "2024-01-15",
        "birth_info": "1965",
    })


def test_update_preserves_unrelated_fields():
    """bug #3 回归：改设置不能丢掉 has_avatar / last_seen / birth_info。"""
    _fresh_config()

    _put(name="妈妈", personality="话很少，但很细心")

    cfg = load_config()
    assert cfg["has_avatar"] is True
    assert cfg["last_seen"] == "2024-01-15"
    assert cfg["birth_info"] == "1965"


def test_update_applies_changed_fields():
    """改动本身要生效。"""
    _fresh_config()

    _put(name="妈妈", personality="话很少，但很细心")

    assert load_config()["personality"] == "话很少，但很细心"


def test_empty_field_keeps_existing_value():
    """请求里没填的字段保持原值，不能被空字符串清掉。"""
    _fresh_config()

    _put(name="妈妈", personality="")

    assert load_config()["personality"] == "话少"


def test_masked_api_key_is_not_written_back():
    """前端回传打码的 key 时，必须保留真实 key。"""
    _fresh_config()

    _put(name="妈妈", api_key="sk-test****")

    assert load_config()["api_key"] == "sk-test"


def test_corrupt_config_falls_back_to_defaults():
    """Review Focus #2：config.json 损坏时不能让应用启动即崩。

    合理预期：降级为默认值，并把坏文件改名保留供排查。
    """
    CONFIG_PATH.write_text("{ 这不是合法 JSON", encoding="utf-8")

    assert load_config() == {}
    assert list(CONFIG_PATH.parent.glob("config.json.corrupt*")), "坏文件应被保留"