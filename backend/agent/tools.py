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
        # 这句话本身是给模型的提示，引导它说「记不太清了」而不是编造
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
