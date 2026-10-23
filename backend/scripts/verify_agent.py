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
from config import load_config

CASES = [
    ("你还记得我们去北京那次吗", "expect:search_memory"),
    ("今天好累啊", "allow_any"),
    ("你说话不像他，他不会这么讲", "expect:record_correction"),
]


def main():
    api_key = load_config().get("api_key", "")
    if not api_key:
        print("config.json 里没有 api_key")
        return

    client = DeepSeekClient(api_key)
    original = client.complete

    for message, expectation in CASES:
        calls = []

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
            "reply_preview": reply[:80],
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()
