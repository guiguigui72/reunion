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


def _load_persona() -> str:
    if PERSONA_PATH.exists():
        return PERSONA_PATH.read_text(encoding="utf-8")
    return ""


def _tool_message(call, result: str) -> dict:
    return {"role": "tool", "tool_call_id": call.id, "content": result}


def _final_reply(client: LLMClient, messages: list[dict], last_content: str) -> str:
    """工具轮次用完时，再要一次「不提供工具」的角色内回复。

    tools 传空数组 = 模型没有可调用的工具，只能说话。
    这里捕获所有异常：这是最后一层，任何失败都必须降级而不是抛出。
    """
    try:
        resp = client.complete(messages, [])
        return resp.content or last_content or STATIC_FALLBACK
    except Exception:
        return last_content or STATIC_FALLBACK


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
