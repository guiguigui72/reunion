# 步骤 4 — Tool Calling 与真正的 Agent 循环 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 `agent/loop.py` 从「意图分类 → 固定流程」的直线，改成「模型自主决定调用工具 → 观察结果 → 继续或作答」的 ReAct 循环，并保证可测试、有步数上限、工具调用可追踪。

**Architecture:** 三层拆分。`agent/llm.py` 定义与供应商无关的 `LLMClient` 协议和归一化的 `LLMResponse`，再提供一个 DeepSeek 适配器 —— 测试用假客户端注入，不碰网络。`agent/tools.py` 集中声明工具 schema 与实现，含一个读工具（检索记忆）和一个写工具（记录纠正），写工具只追加到待审日志、不直接改人格。`agent/loop.py` 只负责循环：调模型、执行工具、把结果喂回去、直到模型不再要求调用工具或达到步数上限。

**Tech Stack:** Python 3.13 / OpenAI SDK（DeepSeek 兼容接口）/ pytest / ChromaDB

**Spec:** `docs/superpowers/specs/2026-10-11-agent-engineering-roadmap-design.md`（§4 步骤 4）

## 现状

```python
def chat(user_message, api_key):
    if is_correction_intent(user_message):        # 关键词判一次
        return handle_correction(...)
    intent = classify_intent(user_message, api_key)  # LLM 判第二次
    if intent["type"] == "correction":
        return handle_correction(...)
    persona = read_persona()
    memories = []
    if intent["type"] == "memory_search":         # 程序决定查不查
        memories = query_collection(...)
    messages = [system] + history(30) + [user]
    return llm(messages).content                  # 一次调用，结束
```

问题：同一件事判两遍；分类看不到历史；模型只能回一个词，没有行动能力；每条消息两次 LLM 调用。

## Global Constraints

- **`chat(user_message, api_key)` 的签名保持不变** —— `api/chat.py` 不应改动。
- **模型不直接改 `persona.md`。** 写操作只追加到 `corrections.jsonl`，等待人工或后续流程合并。
  理由：聊天记录可能含提示注入，任何自动写入人格的路径都必须经审批。
- **必须有不依赖网络的测试。** LLM 客户端通过参数注入，测试用假实现。
- **必须有步数上限**，且上限触发时返回角色内的话，不是报错。
- **工具错误变成工具结果**，交给模型处理，不要让异常打断整轮对话。
- **UI 文案需用户确认** —— 本计划里的降级话术先留占位符。
- 工具栏位控制在 2 个（一读一写）。**不加第三个凑数。**

## Review Focus

1. **模型反复调用同一工具** —— 例如反复 `search_memory("球球")`。上限 + 相同参数去重提示。
2. **并行工具调用** —— 一次返回多个 `tool_calls`。必须按顺序执行并逐一回填结果，`tool_call_id` 不能错配。
3. **工具返回超长内容** —— 5 条记忆全塞进上下文会挤占预算。单条截断 300 字，总长截断 1500 字。
4. **参数 JSON 解析失败 / 缺字段** —— 返回结构化错误让模型重试，不要抛异常。
5. **写入被滥用** —— `record_correction` 单条字段截断 200 字，并要求两个字段都非空。
6. **历史与工具消息的兼容** —— 历史里只有 user/assistant，不含 tool；拼接顺序必须是 system → history → user → 工具往返。

---

## 文件结构

| 文件 | 职责 |
|---|---|
| `backend/agent/llm.py` | `ToolCall` / `LLMResponse` / `LLMClient` 协议 / `DeepSeekClient` |
| `backend/agent/tools.py` | 工具 schema、两个工具实现、`execute_tool` 分发 |
| `backend/agent/loop.py` | 循环本体 + 系统提示词 |
| `backend/config.py` | 新增 `CORRECTIONS_PATH` |
| `backend/tests/test_agent_llm.py` | 适配器的消息转换（用假 SDK 对象） |
| `backend/tests/test_agent_tools.py` | 工具实现与分发 |
| `backend/tests/test_agent_loop.py` | 循环行为（假客户端，多步、上限、错误） |
| `backend/tests/test_agent_prompt.py` | 按新契约更新 |
| `backend/scripts/verify_agent.py` | 真实 API 手动验证（不纳入 pytest） |

---

### Task 1: LLM 抽象层

**Files:**
- Create: `backend/agent/llm.py`、`backend/tests/test_agent_llm.py`

**Interfaces:**
- Produces:
  - `ToolCall(id: str, name: str, arguments: dict, raw: dict)`
  - `LLMResponse(content: str | None, tool_calls: list[ToolCall])`
  - `LLMResponse.to_message() -> dict`
  - `LLMClient` 协议：`complete(messages: list[dict], tools: list[dict]) -> LLMResponse`
  - `DeepSeekClient(api_key: str, model: str = "deepseek-chat")`

- [ ] **Step 1: 写失败测试**

`backend/tests/test_agent_llm.py`：

```python
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


def test_to_message_echoes_tool_calls():
    tc = ToolCall(
        id="call_1", name="search_memory", arguments={"query": "球球"},
        raw={"id": "call_1", "type": "function",
             "function": {"name": "search_memory", "arguments": '{"query": "球球"}'}},
    )
    msg = LLMResponse(content=None, tool_calls=[tc]).to_message()

    assert msg["role"] == "assistant"
    assert msg["tool_calls"][0]["id"] == "call_1"
```

- [ ] **Step 2: 跑，确认失败**

```powershell
cd D:\重逢2\backend
python -m pytest tests/test_agent_llm.py -v
```

Expected: `ImportError: cannot import name 'parse_openai_message'`。

- [ ] **Step 3: 实现**

`backend/agent/llm.py`：

```python
"""与供应商无关的 LLM 抽象。

测试通过注入假 LLMClient 来验证循环逻辑，不需要网络和 API Key。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Protocol

from openai import OpenAI

DEFAULT_MODEL = "deepseek-chat"
DEFAULT_BASE_URL = "https://api.deepseek.com/v1"


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict
    raw: dict
    parse_error: str | None = None


@dataclass
class LLMResponse:
    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)

    def to_message(self) -> dict:
        """转成可以回填进 messages 的 assistant 消息。"""
        msg: dict = {"role": "assistant", "content": self.content or ""}
        if self.tool_calls:
            msg["tool_calls"] = [tc.raw for tc in self.tool_calls]
        return msg


def parse_openai_message(message) -> LLMResponse:
    """把 OpenAI SDK 的 message 对象归一化成 LLMResponse。"""
    calls: list[ToolCall] = []
    for tc in (getattr(message, "tool_calls", None) or []):
        raw_args = tc.function.arguments or ""
        if isinstance(raw_args, dict):
            # 部分 SDK 版本直接给 dict，不是字符串
            arguments, parse_error = raw_args, None
        else:
            try:
                arguments = json.loads(raw_args)
                parse_error = None
            except (json.JSONDecodeError, TypeError) as e:
                arguments = {}
                parse_error = f"参数不是合法 JSON: {e}"

        calls.append(ToolCall(
            id=tc.id,
            name=tc.function.name,
            arguments=arguments,
            raw={
                "id": tc.id,
                "type": "function",
                "function": {"name": tc.function.name, "arguments": raw_args},
            },
            parse_error=parse_error,
        ))

    return LLMResponse(content=getattr(message, "content", None), tool_calls=calls)


class LLMClient(Protocol):
    def complete(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        ...


class DeepSeekClient:
    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        self._client = OpenAI(api_key=api_key, base_url=DEFAULT_BASE_URL)
        self._model = model

    def complete(self, messages: list[dict], tools: list[dict],
                 temperature: float = 0.7, max_tokens: int = 1024) -> LLMResponse:
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            tools=tools or None,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return parse_openai_message(resp.choices[0].message)
```

- [ ] **Step 4: 跑，确认通过**

```powershell
python -m pytest tests/test_agent_llm.py -v
```

Expected: 4 passed。

- [ ] **Step 5: 提交**

```powershell
cd D:\重逢2
git add backend/agent/llm.py backend/tests/test_agent_llm.py
git status
git commit -m "feat: add provider-neutral LLM abstraction for tool calling" -m "把 OpenAI/DeepSeek 的响应归一化成 LLMResponse，循环逻辑不再依赖 SDK 对象形状。参数 JSON 解析失败时降级为空 dict 并记录 parse_error，交给循环转成工具错误。测试可注入假客户端，不碰网络。"
git show --stat HEAD
```

---

### Task 2: 工具层

**Files:**
- Create: `backend/agent/tools.py`、`backend/tests/test_agent_tools.py`
- Modify: `backend/config.py`

**Interfaces:**
- Produces:
  - `TOOL_SCHEMAS: list[dict]`
  - `search_memory(query: str, n_results: int = 5) -> str`
  - `record_correction(what_was_wrong: str, correct_behavior: str) -> str`
  - `execute_tool(name: str, arguments: dict) -> str`
  - `config.CORRECTIONS_PATH: Path`

- [ ] **Step 1: 加纠正日志路径**

`backend/config.py` 顶部常量区追加：

```python
CORRECTIONS_PATH = DATA_DIR / "corrections.jsonl"
```

- [ ] **Step 2: 写失败测试**

`backend/tests/test_agent_tools.py`：

```python
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
```

- [ ] **Step 3: 跑，确认失败**

```powershell
python -m pytest tests/test_agent_tools.py -v
```

Expected: `ModuleNotFoundError: No module named 'agent.tools'`。

- [ ] **Step 4: 实现**

`backend/agent/tools.py`：

```python
"""工具声明与实现。

设计原则：
- 读工具与写工具分开命名，写操作只追加待审日志，不直接改人格
- 工具错误返回文字给模型，不抛异常中断整轮对话
- 返回内容有长度上限，避免挤占上下文预算
"""
from __future__ import annotations

import json
import time

from config import CORRECTIONS_PATH, ensure_data_dir
from rag.embedder import embed_texts
from rag.store import query_collection

MAX_DOC_CHARS = 300
MAX_TOTAL_CHARS = 1500
MAX_FIELD_CHARS = 200

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "search_memory",
            "description": (
                "在用户的聊天记录里检索与当前话题相关的往事。"
                "当用户提到过去的人、事、地点或时间，或问你还记不记得什么时使用。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "检索关键词，或一句话描述要查的往事",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "record_correction",
            "description": (
                "当用户指出你的说法、语气或记忆不像本人时，记录这次纠正。"
                "只在用户明确纠正你时使用，不要用于普通聊天。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "what_was_wrong": {
                        "type": "string",
                        "description": "你刚才哪里说得不对",
                    },
                    "correct_behavior": {
                        "type": "string",
                        "description": "用户指出应该怎样",
                    },
                },
                "required": ["what_was_wrong", "correct_behavior"],
            },
        },
    },
]


def search_memory(query: str, n_results: int = 5) -> str:
    """返回格式化的记忆片段，总长受限。"""
    embedding = embed_texts([query])[0]
    docs = query_collection(embedding, n_results=n_results)
    if not docs:
        return "没有找到相关的往事。"

    parts: list[str] = []
    total = 0
    for i, doc in enumerate(docs, start=1):
        piece = f"[{i}] {doc.strip()[:MAX_DOC_CHARS]}"
        if total + len(piece) > MAX_TOTAL_CHARS:
            break
        parts.append(piece)
        total += len(piece)
    return "\n\n".join(parts)


def record_correction(what_was_wrong: str, correct_behavior: str) -> str:
    """追加一条待审纠正记录。不直接修改 persona.md。"""
    what_was_wrong = (what_was_wrong or "").strip()[:MAX_FIELD_CHARS]
    correct_behavior = (correct_behavior or "").strip()[:MAX_FIELD_CHARS]
    if not what_was_wrong or not correct_behavior:
        raise ValueError("两个字段都不能为空")

    ensure_data_dir()
    entry = {
        "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "what_was_wrong": what_was_wrong,
        "correct_behavior": correct_behavior,
    }
    with open(CORRECTIONS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return "已记录这次纠正。"


TOOL_IMPL = {
    "search_memory": search_memory,
    "record_correction": record_correction,
}

REQUIRED_ARGS = {
    "search_memory": ("query",),
    "record_correction": ("what_was_wrong", "correct_behavior"),
}


def execute_tool(name: str, arguments: dict) -> str:
    """执行工具，任何异常都转成给模型看的文字。"""
    if name not in TOOL_IMPL:
        return f"未知工具：{name}"

    missing = [a for a in REQUIRED_ARGS[name] if not arguments.get(a)]
    if missing:
        return f"缺少参数：{', '.join(missing)}"

    try:
        return TOOL_IMPL[name](**{a: arguments[a] for a in REQUIRED_ARGS[name]})
    except Exception as e:
        return f"工具 {name} 执行失败：{e}"
```

> 注意：`search_memory` 用 `**kwargs` 调用时只传 `required` 里的参数，
> 这样 `n_results` 走默认值。测试里 monkeypatch 的替身也必须接受这些参数。

- [ ] **Step 5: 跑，确认通过**

```powershell
python -m pytest tests/test_agent_tools.py -v
```

Expected: 8 passed。

- [ ] **Step 6: 提交**

```powershell
git add backend/agent/tools.py backend/config.py backend/tests/test_agent_tools.py
git status
git commit -m "feat: add tool layer with one read and one write tool" -m "search_memory 检索往事并按长度截断；record_correction 只追加 corrections.jsonl 待审，不直接修改 persona。工具异常统一转成文字返回给模型，避免中断整轮对话。"
git show --stat HEAD
```

---

### Task 3: ReAct 循环

**Files:**
- Modify: `backend/agent/loop.py`（重写 `chat`）
- Modify: `backend/tests/test_agent_prompt.py`
- Create: `backend/tests/test_agent_loop.py`

**Interfaces:**
- Consumes: `agent.llm.LLMClient`、`agent.tools.TOOL_SCHEMAS`、`agent.tools.execute_tool`
- Produces: `agent.loop.chat(user_message: str, api_key: str, client=None, max_steps: int = 5) -> str`
- Produces: `agent.loop.build_system_prompt(persona: str) -> str`（**签名变了**）

- [ ] **Step 1: 更新系统提示词测试**

`backend/tests/test_agent_prompt.py` 整个替换为：

```python
from agent.loop import build_system_prompt

PERSONA = "# 妈妈 — Relationship Persona\n\n说话简短，爱用「嗯」。"
TOOL_NAMES = ("search_memory", "record_correction")


def test_persona_always_present():
    assert PERSONA in build_system_prompt(PERSONA)


def test_no_empty_memory_section_injected():
    """bug #1 的不变量：永远不要往提示词里塞「暂无相关记忆」。
    记忆改由 search_memory 在运行时获取。"""
    prompt = build_system_prompt(PERSONA)

    assert "暂无相关记忆" not in prompt
    assert "记忆片段\n" not in prompt


def test_tool_usage_guidance_present():
    prompt = build_system_prompt(PERSONA)

    for name in TOOL_NAMES:
        assert name in prompt


def test_never_fabricate_rule_always_present():
    assert "绝不编造" in build_system_prompt(PERSONA)


def test_empty_persona_does_not_crash():
    prompt = build_system_prompt("")

    assert isinstance(prompt, str)
    assert "暂无相关记忆" not in prompt
```

- [ ] **Step 2: 写循环测试**

`backend/tests/test_agent_loop.py`：

```python
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
        return self._script.pop(0)


def _call(id_, name, args, raw=None):
    return ToolCall(
        id=id_, name=name, arguments=args,
        raw=raw or {"id": id_, "type": "function",
                    "function": {"name": name, "arguments": "{}"}},
    )


@pytest.fixture(autouse=True)
def _no_persona(monkeypatch, tmp_path):
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

    assert seen_tools[0]                 # 正常轮次有工具
    assert seen_tools[-1] == []          # 收尾轮次没有


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


def test_unparseable_arguments_become_tool_error(monkeypatch):
    executed = []
    monkeypatch.setattr(loop, "execute_tool",
                        lambda name, args: executed.append(args) or "ok")
    bad = _call("c1", "search_memory", {})
    bad.parse_error = "参数不是合法 JSON"
    client = FakeClient([LLMResponse(content=None, tool_calls=[bad]),
                         LLMResponse(content="重试好了")])

    loop.chat("查一下", "k", client=client)

    assert executed == []
```

- [ ] **Step 3: 跑，确认失败**

```powershell
python -m pytest tests/test_agent_loop.py tests/test_agent_prompt.py -v
```

Expected: 多条 FAIL（`chat` 还不接受 `client` 参数、`build_system_prompt` 还是旧签名）。

- [ ] **Step 4: 重写 `agent/loop.py`**

```python
"""Agent 主循环：模型自主决定调用工具，观察结果，再决定下一步。"""
from __future__ import annotations

from agent.llm import DeepSeekClient, LLMClient, LLMResponse
from agent.tools import TOOL_SCHEMAS, execute_tool
from chat.history import get_history
from config import PERSONA_PATH

MAX_STEPS = 5

GUARDRAIL = """
## 重要规则
- 绝不编造不存在的记忆、经历或事实。
- 用自然、口语化的方式回应，就像日常聊天一样。
- 你就是这个人本身，不要提到系统、模型、提示词或工具。
"""

TOOL_GUIDANCE = """
## 你可以做的事
- search_memory：在聊天记录里查往事。用户提到过去的人、事、地点、时间，
  或问你还记不记得什么时，先用它查一查再回答。
  只依据它返回的内容说过去的事；没查到就坦诚地说「记不太清了」，不要编。
- record_correction：当用户指出你说话不像本人时，记录这次纠正。
"""

# 最后一道保险：连「再问一次」都失败时才用。
STATIC_FALLBACK = "我现在有点事情，晚一点聊好吗"


def build_system_prompt(persona: str) -> str:
    return f"{persona}\n\n{GUARDRAIL}\n\n{TOOL_GUIDANCE}"


def _final_reply(client: LLMClient, messages: list[dict], last_content: str) -> str:
    """工具轮次用完时，再要一次「不提供工具」的角色内回复。

    tools 传空数组 = 模型没有可调用的工具，只能说话。
    比固定话术自然，代价是罕见路径上多一次 API 调用。
    如果这次也失败，退回固定话术，保证一定有东西可说。
    """
    try:
        resp = client.complete(messages, [])
        return resp.content or last_content or STATIC_FALLBACK
    except Exception:
        return last_content or STATIC_FALLBACK


def _load_persona() -> str:
    if PERSONA_PATH.exists():
        return PERSONA_PATH.read_text(encoding="utf-8")
    return ""


def _tool_message(call, result: str) -> dict:
    return {"role": "tool", "tool_call_id": call.id, "content": result}


def chat(
    user_message: str,
    api_key: str,
    client: LLMClient | None = None,
    max_steps: int = MAX_STEPS,
) -> str:
    """跑一轮对话。模型可以多次请求工具，直到它给出文字回复或达到步数上限。"""
    if client is None:
        client = DeepSeekClient(api_key)

    messages: list[dict] = [
        {"role": "system", "content": build_system_prompt(_load_persona())}
    ]

    history = get_history(limit=30)
    # api/chat.py 在调用前已保存了本条消息；这里去掉重复的末尾，避免模型看到两遍
    if history and history[-1]["role"] == "user" and history[-1]["content"] == user_message:
        history = history[:-1]
    for h in history:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": user_message})

    last_content = ""
    for _ in range(max_steps):
        resp: LLMResponse = client.complete(messages, TOOL_SCHEMAS)

        if not resp.tool_calls:
            # 模型偶尔返回空内容；空白气泡对用户是坏体验，兜底到固定话术
            return resp.content or last_content or STATIC_FALLBACK

        last_content = resp.content or last_content
        messages.append(resp.to_message())

        for call in resp.tool_calls:
            if call.parse_error:
                result = f"调用失败：{call.parse_error}"
            else:
                result = execute_tool(call.name, call.arguments)
            messages.append(_tool_message(call, result))

    return _final_reply(client, messages, last_content)
```

- [ ] **Step 5: 跑，确认通过**

```powershell
python -m pytest tests/test_agent_loop.py tests/test_agent_prompt.py -v
python -m pytest -v
```

Expected: 8 + 5 通过；全量 **47 passed**（原 33 + 4 + 8 + 2）。

- [ ] **Step 6: 提交**

```powershell
git add backend/agent/loop.py backend/tests/test_agent_loop.py backend/tests/test_agent_prompt.py
git status
git commit -m "feat: replace intent classification with a tool-calling agent loop" -m "模型自主决定何时检索记忆、何时记录纠正，循环直到给出文字回复或达到步数上限。删除关键词判纠错与三分类调用，每条消息的 LLM 调用从固定两次变为按需。工具错误与参数解析失败都作为工具结果回传，不中断对话。"
git show --stat HEAD
```

---

### Task 4: 提示词与真实 API 验证

**Files:**
- Modify: `backend/agent/loop.py`（确认话术）
- Create: `backend/scripts/verify_agent.py`
- Modify: `README.md`（把「线性流程」改回「tool-calling 循环」）

- [ ] **Step 1: 降级话术（已确认）**

`STATIC_FALLBACK = "我现在有点事情，晚一点聊好吗"`

只在前两层兜底都失败时出现：

1. 5 轮工具调用用完 → 再问一次（不提供工具），让模型自己说一句角色内的话
2. 那次调用也失败 → 用上面这句固定话术 |

- [ ] **Step 2: 写验证脚本**

`backend/scripts/verify_agent.py`：

```python
"""用真实 DeepSeek API 验证工具调用是否发生。

用法：
  cd backend
  python scripts/verify_agent.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent import loop
from agent.llm import DeepSeekClient
from agent.tools import TOOL_SCHEMAS
from config import load_config

CASES = [
    ("你还记得我们去北京那次吗", "expect_tool"),
    ("今天好累啊", "allow_any"),
    ("你说话不像他，他不会这么讲", "expect_tool"),
]


def main():
    api_key = load_config().get("api_key", "")
    if not api_key:
        print("config.json 里没有 api_key")
        return

    client = DeepSeekClient(api_key)

    for message, expectation in CASES:
        calls = []
        original = client.complete

        def spy(messages, tools, **kw):
            resp = original(messages, tools, **kw)
            calls.extend(tc.name for tc in resp.tool_calls)
            return resp

        client.complete = spy
        reply = loop.chat(message, api_key, client=client)
        client.complete = original

        print(json.dumps({
            "message": message,
            "expectation": expectation,
            "tools_called": calls,
            "reply_preview": reply[:60],
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: 跑验证**

```powershell
cd D:\重逢2\backend
python scripts/verify_agent.py
```

Expected：
- 「北京」那条调用 `search_memory`
- 「今天好累啊」可以不调用任何工具
- 纠错那条调用 `record_correction`
- 所有回复保持在角色内（不含「系统」「模型」「工具」等词）

**如果模型不调用工具**，先检查工具描述是否够明确，再考虑在系统提示里加强指引。

- [ ] **Step 4: 更新 README**

把附录里的：

```markdown
- **线性处理流程**：意图分类（闲聊/记忆搜索/纠错）→ 选择性 RAG 检索 → 人格化回复
  （当前是线性流程；步骤 4 将改为 tool-calling 驱动的 agent 循环）
```

改为：

```markdown
- **Agent 循环**：模型自主决定调用 `search_memory` / `record_correction`，
  观察结果后继续推理或作答，最多 5 步
```

- [ ] **Step 5: 提交**

```powershell
git add backend/agent/loop.py backend/scripts/verify_agent.py README.md
git status
git commit -m "docs: verify tool-calling agent against real API" -m "..."
git show --stat HEAD
```

---

### Task 5: ADR 与收尾

- [ ] **Step 1: 写 ADR-0008**

`docs/decisions/0008-tool-calling-loop.md`，包含：

- 背景：原实现同一件事判两遍、分类不带历史、模型无行动能力
- 备选方案：保留意图分类 / 用 LangGraph / 手写循环
- 决定：手写 ReAct 循环
- 理由：3 个工具以内、无持久化执行与人机中断需求，图编排不划算
- 工具设计：一读一写；写操作只追加待审日志
- 已知限制：纠错尚未自动合并进 persona；无并发控制
- 验证结果：三条样例的工具调用情况

- [ ] **Step 2: 清理废弃代码**

确认 `persona/correction.py` 与 `prompts/correction_handler.md` 是否还有引用：

```powershell
cd D:\重逢2\backend
grep -rn "correction_handler\|is_correction_intent\|handle_correction" --include="*.py" --include="*.md" .
```

若无引用，在 ADR 中记录「已废弃，保留文件待后续清理」，**本步骤不删**（避免一次改动做两件事）。

- [ ] **Step 3: 提交**

```powershell
git add docs/decisions/0008-tool-calling-loop.md
git commit -m "docs: record tool-calling loop decision and limitations"
git show --stat HEAD
```

---

## 完成标准

- [ ] `python -m pytest -v` → 47 passed
- [ ] `python scripts/verify_agent.py` 三条样例的调用符合预期
- [ ] `api/chat.py` 未改动，接口行为保持兼容
- [ ] `record_correction` 写入 `~/.reunion/corrections.jsonl`，不碰 `persona.md`
- [ ] 能口头回答：
  - 为什么不用 LangGraph？
  - 为什么写工具只追加日志、不直接改人格？
  - 步数上限触发时为什么不能抛异常？
  - 工具错误为什么要转成文字给模型，而不是抛出去？
