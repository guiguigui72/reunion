"""Agent 工具选择评估。

用真实 API 跑一组用例，检查模型是否调用了正确的工具。
在临时 REUNION_HOME 下运行，不碰真实数据。

用法：
  cd backend
  python -m evals.agent
"""
from __future__ import annotations

import os
import tempfile

# 必须在导入项目模块之前设置
os.environ["REUNION_HOME"] = tempfile.mkdtemp(prefix="reunion-agent-eval-")

import argparse  # noqa: E402
import json  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

from agent import loop  # noqa: E402
from agent.llm import DeepSeekClient  # noqa: E402

RESULTS_DIR = Path(__file__).parent.parent / "results"

# expectation: search_memory / record_correction / none / any
CASES = [
    {"message": "你还记得我们去北京那次吗", "expect": "search_memory"},
    {"message": "球球最近怎么样", "expect": "search_memory"},
    {"message": "我妈以前是不是特别爱唠叨", "expect": "search_memory"},
    {"message": "你还记得我小时候那次发烧吗", "expect": "search_memory"},
    {"message": "今天好累啊", "expect": "none"},
    {"message": "在吗", "expect": "none"},
    {"message": "晚上吃什么好", "expect": "none"},
    {"message": "最近工作有点忙", "expect": "none"},
    {"message": "你说话不像他，他不会这么讲", "expect": "record_correction"},
    {"message": "别这么说，她不会这样讲话的", "expect": "record_correction"},
]


def read_real_api_key() -> str:
    path = Path.home() / ".reunion" / "config.json"
    if not path.exists():
        return ""
    return json.loads(path.read_text(encoding="utf-8")).get("api_key", "")


def judge(expected: str, calls: list[str]) -> bool:
    if expected == "none":
        return not calls
    if expected == "any":
        return bool(calls)
    return expected in calls


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeat", type=int, default=1, help="每个用例重复次数")
    args = parser.parse_args()

    api_key = read_real_api_key()
    if not api_key:
        print("没有找到 api_key")
        return

    client = DeepSeekClient(api_key)
    original = client.complete

    results = []
    for case in CASES:
        runs = []
        for _ in range(args.repeat):
            calls: list[str] = []

            def spy(messages, tools, **kw):
                resp = original(messages, tools, **kw)
                calls.extend(tc.name for tc in resp.tool_calls)
                return resp

            client.complete = spy
            reply = loop.chat(case["message"], api_key, client=client)
            client.complete = original

            runs.append({"calls": calls, "pass": judge(case["expect"], calls),
                         "reply": reply[:60]})

        results.append({**case, "runs": runs})

    total = sum(len(r["runs"]) for r in results)
    passed = sum(1 for r in results for run in r["runs"] if run["pass"])
    strict = sum(1 for r in results if all(run["pass"] for run in r["runs"]))

    summary = {
        "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "cases": len(results),
        "repeat": args.repeat,
        "pass@1": round(passed / total, 4) if total else 0.0,
        f"pass^{args.repeat}": round(strict / len(results), 4) if results else 0.0,
    }

    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"agent_{time.strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(
        json.dumps({"summary": summary, "results": results},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    for r in results:
        marks = "".join("✅" if run["pass"] else "❌" for run in r["runs"])
        last = r["runs"][-1]
        print(f"{marks} {r['message'][:20]:<22} expect={r['expect']:<18} calls={last['calls']}")

    print()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"结果已写入 {out}")


if __name__ == "__main__":
    main()
