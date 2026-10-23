import json

import pytest

from agent import tools
from config import CORRECTIONS_PATH


def test_search_memory_formats_hits(monkeypatch):
    monkeypatch.setattr(tools, "query_collection", lambda emb, n_results=5: ["片段一", "片段二"])
    monkeypatch.setattr(tools, "embed_texts", lambda texts: [[0.0, 0.0]])

    out = tools.search_memory("球球")

    assert "片段一" in out and "片段二" in out


def test_search_memory_empty_returns_hint(monkeypatch):
    monkeypatch.setattr(tools, "query_collection", lambda emb, n_results=5: [])
    monkeypatch.setattr(tools, "embed_texts", lambda texts: [[0.0, 0.0]])

    assert "没有找到" in tools.search_memory("不存在的事")


def test_search_memory_truncates_long_docs(monkeypatch):
    long = "啊" * 1000
    monkeypatch.setattr(tools, "query_collection", lambda emb, n_results=5: [long])
    monkeypatch.setattr(tools, "embed_texts", lambda texts: [[0.0, 0.0]])

    out = tools.search_memory("x")
    assert len(out) < 400


def test_record_correction_appends_jsonl():
    tools.record_correction("说成了南方口音", "他其实是北方人")

    lines = CORRECTIONS_PATH.read_text(encoding="utf-8").strip().splitlines()
    entry = json.loads(lines[-1])
    assert entry["what_was_wrong"] == "说成了南方口音"
    assert entry["correct_behavior"] == "他其实是北方人"


def test_record_correction_rejects_empty():
    with pytest.raises(ValueError):
        tools.record_correction("", "x")
    with pytest.raises(ValueError):
        tools.record_correction("x", "")


def test_execute_tool_unknown_name_returns_message():
    out = tools.execute_tool("delete_everything", {})
    assert "未知工具" in out


def test_execute_tool_handles_missing_argument():
    out = tools.execute_tool("search_memory", {})
    assert "缺少参数" in out


def test_execute_tool_catches_exceptions(monkeypatch):
    def boom(**kwargs):
        raise RuntimeError("索引坏了")

    monkeypatch.setitem(tools.TOOL_IMPL, "search_memory", boom)

    out = tools.execute_tool("search_memory", {"query": "x"})
    assert "索引坏了" in out
