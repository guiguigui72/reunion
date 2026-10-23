import asyncio

from api import chat as chat_api


def test_chat_endpoint_returns_reply(monkeypatch):
    monkeypatch.setattr(chat_api, "load_config", lambda: {"api_key": "sk-test"})
    monkeypatch.setattr(chat_api, "save_message", lambda *a, **kw: None)
    monkeypatch.setattr(chat_api, "get_history", lambda limit=50: [])
    monkeypatch.setattr(chat_api, "agent_chat",
                        lambda message, key: f"回复:{message}")

    res = asyncio.run(chat_api.chat_endpoint(
        chat_api.ChatRequest(message="你好")
    ))

    assert res.reply == "回复:你好"


def test_chat_endpoint_requires_api_key(monkeypatch):
    import pytest

    monkeypatch.setattr(chat_api, "load_config", lambda: {})

    with pytest.raises(chat_api.HTTPException) as exc:
        asyncio.run(chat_api.chat_endpoint(chat_api.ChatRequest(message="你好")))

    assert exc.value.status_code == 400
