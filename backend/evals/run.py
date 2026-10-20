"""检索评估 CLI。

用法：
  python -m evals.run --chat-log "C:\\path\\to\\chat.txt" --target 妈妈 --limit 40
"""
from __future__ import annotations

import os
import tempfile

# 必须在导入项目模块之前设置 —— config.py 在模块级读取它。
# 直接赋值（不是 setdefault）：确保评估永远不碰真实记忆库。
os.environ["REUNION_HOME"] = tempfile.mkdtemp(prefix="reunion-eval-")

import argparse  # noqa: E402
import json  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

from evals.golden import build_golden  # noqa: E402
from evals.retrieval import build_index, retrieve, score_all  # noqa: E402

RESULTS_DIR = Path(__file__).parent.parent / "results"
GOLDEN_DIR = Path(__file__).parent.parent / "golden"
MODEL_NAME = "BAAI/bge-small-zh-v1.5"


def load_chat(path: str) -> str:
    raw = Path(path).read_bytes()
    for enc in ("utf-8-sig", "utf-8", "utf-16", "gbk"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"无法识别编码: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="检索质量评估")
    parser.add_argument("--chat-log", required=True, help="聊天记录文件路径")
    parser.add_argument("--target", default="妈妈", help="导出文件中目标人物的标签")
    parser.add_argument("--limit", type=int, default=40, help="golden set 条数上限")
    parser.add_argument("--top-k", type=int, default=5, help="检索返回条数")
    parser.add_argument("--min-question-len", type=int, default=8,
                        help="弱标记问题的长度下限，过滤「是吗？」这类附和")
    parser.add_argument("--min-answer-len", type=int, default=15,
                        help="证据的最小长度，过滤「记得啊」这类空回复")
    args = parser.parse_args()

    chat_log = load_chat(args.chat_log)

    items = build_golden(
        chat_log,
        args.target,
        min_question_len=args.min_question_len,
        min_answer_len=args.min_answer_len,
        limit=args.limit,
    )
    if not items:
        print(
            f"没有构建出任何 golden item —— 检查 --target 是否与导出里的标签一致"
            f"（当前: {args.target!r}）"
        )
        return

    GOLDEN_DIR.mkdir(exist_ok=True)
    golden_path = GOLDEN_DIR / "real_golden.jsonl"
    golden_path.write_text(
        "\n".join(json.dumps(i, ensure_ascii=False) for i in items) + "\n",
        encoding="utf-8",
    )
    print(f"golden set 已写入 {golden_path}（{len(items)} 条）")

    target_chars, n_chunks = build_index(chat_log, args.target)
    print(f"索引完成：目标文本 {target_chars} 字符，切分为 {n_chunks} 块")

    retrieved_map = {
        item["id"]: retrieve(item["question"], n_results=args.top_k)
        for item in items
    }
    metrics = score_all(items, retrieved_map)

    result = {
        "time": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "corpus": {"target_chars": target_chars, "chunks": n_chunks},
        "golden": {"items": len(items), "source": str(golden_path.name)},
        "metrics": metrics,
        "config": {
            "model": MODEL_NAME,
            "space": "cosine",
            "top_k": args.top_k,
            "min_question_len": args.min_question_len,
            "min_answer_len": args.min_answer_len,
        },
    }

    RESULTS_DIR.mkdir(exist_ok=True)
    out = RESULTS_DIR / f"retrieval_{time.strftime('%Y%m%d_%H%M%S')}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"\n结果已写入 {out}")


if __name__ == "__main__":
    main()
