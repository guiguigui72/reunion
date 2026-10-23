import pytest

from agent import loop
from agent.llm import LLMResponse, ToolCall


class FakeClient:
    """按脚本逐次返回预设响应，并记录每次收到的 messages。"""

    def __init__(self, script):
        self._script = list(script)
        self.calls = []

    def complete(self, messages, tools, **kwargs):
        self.calls.append([dict(m) for m in messages])
        if not self._script:
            raise AssertionError("FakeClient 脚本用完了")
        return self._script.pop(0)


def _call(id_, name, args, raw=None):
    return ToolCall(
        id=id_, name=name, arguments=args,
        raw=raw or {"id": id_, "type": "function",
                    "function": {"name": name, "arguments": "{}"}},
    )


@pytest.fixture(autouse=True)
def _isolate(monkeypatch, tmp_path):
    monkeypatch.setattr(loop, "PERSONA_PATH", tmp_path / "persona.md")
    monkeypatch.setattr(loop, "get_history", lambda limit=30: [])
    monkeypatch.setattr(loop, "execute_tool", lambda name, args: f"结果:{name}")


def test_plain_reply_returns_immediately():
    client = FakeClient([LLMResponse(content="今天还好")])

    assert loop.chat("今天怎么样", "k", client=client) == "今天还好"
    assert len(client.calls) == 1


def test_tool_call_then_reply_is_two_rounds():
    client = FakeClient([
        LLMResponse(content=None, tool_calls=[_call("c1", "search_memory", {"query": "球球"})]),
        LLMResponse(content="球球还是老样子"),
    ])

    reply = loop.chat("球球最近怎么样", "k", client=client)

    assert reply == "球球还是老样子"
    assert len(client.calls) == 2
    # 第二轮必须能看到 tool 结果
    second = client.calls[1]
    assert any(m.get("role") == "tool" and "结果:search_memory" in m.get("content", "")
               for m in second)


def test_parallel_tool_calls_get_matching_ids():
    client = FakeClient([
        LLMResponse(content=None, tool_calls=[
            _call("c1", "search_memory", {"query": "球球"}),
            _call("c2", "record_correction",
                  {"what_was_wrong": "a", "correct_behavior": "b"}),
        ]),
        LLMResponse(content="记住了"),
    ])

    loop.chat("球球怎么样，另外你说话不像他", "k", client=client)

    tool_msgs = [m for m in client.calls[1] if m.get("role") == "tool"]
    assert [m["tool_call_id"] for m in tool_msgs] == ["c1", "c2"]


def test_current_message_is_not_duplicated(monkeypatch):
    """api/chat.py 在调用 chat() 之前就已把用户消息存进历史，
    chat() 又把它追加一次 —— 模型会看到同一句话两遍。"""
    monkeypatch.setattr(
        loop, "get_history",
        lambda limit=30: [{"role": "user", "content": "你好"}],
    )
    client = FakeClient([LLMResponse(content="嗯")])

    loop.chat("你好", "k", client=client)

    user_msgs = [m for m in client.calls[0] if m["role"] == "user"]
    assert len(user_msgs) == 1


def test_empty_content_falls_back():
    """模型返回空文字且无工具调用时，不能给用户一个空气泡。"""
    client = FakeClient([LLMResponse(content="")])

    assert loop.chat("在吗", "k", client=client) == loop.STATIC_FALLBACK


def test_max_steps_asks_llm_for_in_character_reply():
    """轮次用完后再问一次，且这次不提供任何工具。"""
    script = [
        LLMResponse(content=None, tool_calls=[_call(f"c{i}", "search_memory", {"query": "x"})])
        for i in range(3)
    ] + [LLMResponse(content="（愣了一下）……你刚才说什么？")]

    client = FakeClient(script)
    reply = loop.chat("一直查", "k", client=client, max_steps=3)

    assert reply == "（愣了一下）……你刚才说什么？"
    # 3 轮工具 + 1 轮收尾
    assert len(client.calls) == 4


def test_final_call_has_no_tools():
    """收尾那次必须传空工具列表，模型才只能说话。"""
    script = [
        LLMResponse(content=None, tool_calls=[_call("c1", "search_memory", {"query": "x"})])
    ] + [LLMResponse(content="嗯……")]

    seen_tools = []

    class SpyClient(FakeClient):
        def complete(self, messages, tools, **kw):
            seen_tools.append(tools)
            return super().complete(messages, tools, **kw)

    client = SpyClient(script)
    loop.chat("查一下", "k", client=client, max_steps=1)

    assert seen_tools[0]
    assert seen_tools[-1] == []


def test_final_call_failure_uses_static_fallback():
    class BrokenFinal(FakeClient):
        def complete(self, messages, tools, **kw):
            if tools == []:
                raise RuntimeError("网络断了")
            return super().complete(messages, tools, **kw)

    script = [
        LLMResponse(content=None, tool_calls=[_call("c1", "search_memory", {"query": "x"})])
    ]
    client = BrokenFinal(script)

    assert loop.chat("查一下", "k", client=client, max_steps=1) == loop.STATIC_FALLBACK


def test_tool_error_is_fed_back_not_raised(monkeypatch):
    monkeypatch.setattr(loop, "execute_tool", lambda name, args: "工具执行失败：索引坏了")
    client = FakeClient([
        LLMResponse(content=None, tool_calls=[_call("c1", "search_memory", {"query": "x"})]),
        LLMResponse(content="那我记不太清了"),
    ])

    assert loop.chat("你还记得吗", "k", client=client) == "那我记不太清了"


def test_unparseable_arguments_become_tool_error(monkeypatch):
    executed = []
    monkeypatch.setattr(loop, "execute_tool",
                        lambda name, args: executed.append(args) or "ok")
    bad = _call("c1", "search_memory", {})
    bad.parse_error = "参数不是合法 JSON"
    client = FakeClient([LLMResponse(content=None, tool_calls=[bad]),
                         LLMResponse(content="重试好了")])

    reply = loop.chat("查一下", "k", client=client)

    assert executed == []
    assert reply == "重试好了"
