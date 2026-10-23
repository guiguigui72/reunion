import json

from agent.llm import LLMResponse, ToolCall, parse_openai_message


class _Fn:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class _Call:
    def __init__(self, id_, name, arguments):
        self.id = id_
        self.function = _Fn(name, arguments)


class _Msg:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


def test_plain_reply_has_no_tool_calls():
    resp = parse_openai_message(_Msg(content="今天还好"))
    assert resp.content == "今天还好"
    assert resp.tool_calls == []


def test_tool_call_arguments_are_parsed():
    raw = _Call("call_1", "search_memory", '{"query": "球球"}')
    resp = parse_openai_message(_Msg(content=None, tool_calls=[raw]))

    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0].name == "search_memory"
    assert resp.tool_calls[0].arguments == {"query": "球球"}
    assert resp.tool_calls[0].id == "call_1"


def test_invalid_arguments_do_not_crash():
    """模型偶尔会返回非法 JSON —— 不能在这里炸掉整轮对话。"""
    raw = _Call("call_2", "search_memory", "{not json")
    resp = parse_openai_message(_Msg(content=None, tool_calls=[raw]))

    assert resp.tool_calls[0].arguments == {}
    assert resp.tool_calls[0].parse_error is not None


def test_dict_arguments_are_accepted():
    """部分 SDK 版本直接给 dict，不是字符串。"""
    raw = _Call("call_3", "search_memory", {"query": "球球"})
    resp = parse_openai_message(_Msg(content=None, tool_calls=[raw]))

    assert resp.tool_calls[0].arguments == {"query": "球球"}
    assert resp.tool_calls[0].parse_error is None


def test_to_message_echoes_tool_calls():
    tc = ToolCall(
        id="call_1", name="search_memory", arguments={"query": "球球"},
        raw={"id": "call_1", "type": "function",
             "function": {"name": "search_memory", "arguments": json.dumps({"query": "球球"})}},
    )
    msg = LLMResponse(content=None, tool_calls=[tc]).to_message()

    assert msg["role"] == "assistant"
    assert msg["tool_calls"][0]["id"] == "call_1"
