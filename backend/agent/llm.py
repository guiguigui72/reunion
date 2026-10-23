"""与供应商无关的 LLM 抽象。

测试通过注入假 LLMClient 来验证循环逻辑，不需要网络和 API Key。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Protocol

from openai import OpenAI

DEFAULT_MODEL = "deepseek-flash"
DEFAULT_BASE_URL = "https://api.deepseek.com/v1"


@dataclass
class ToolCall:
    """一次工具调用。raw 保留 SDK 原始格式，回填 messages 时原样使用。"""

    id: str
    name: str
    arguments: dict
    raw: dict
    parse_error: str | None = None


@dataclass
class LLMResponse:
    """归一化后的模型回复：要么是文字，要么是若干工具调用。"""

    content: str | None = None
    tool_calls: list[ToolCall] = field(default_factory=list)

    def to_message(self) -> dict:
        """转成可以回填进 messages 的 assistant 消息。"""
        msg: dict = {"role": "assistant", "content": self.content or ""}
        if self.tool_calls:
            msg["tool_calls"] = [tc.raw for tc in self.tool_calls]
        return msg


def parse_openai_message(message) -> LLMResponse:
    """把 OpenAI SDK 的 message 对象归一化成 LLMResponse。

    参数不是合法 JSON 时不抛异常 —— 记在 parse_error 里，
    由循环转成工具错误回传，让模型有机会重试。
    """
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
    """任何实现了 complete() 的对象都可以注入给循环。"""

    def complete(self, messages: list[dict], tools: list[dict]) -> LLMResponse:
        ...


class DeepSeekClient:
    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        self._client = OpenAI(api_key=api_key, base_url=DEFAULT_BASE_URL)
        self._model = model

    def complete(
        self,
        messages: list[dict],
        tools: list[dict],
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            tools=tools or None,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return parse_openai_message(resp.choices[0].message)
