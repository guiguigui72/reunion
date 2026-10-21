from langchain_text_splitters import RecursiveCharacterTextSplitter


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]:
    """
    Split raw chat log into overlapping chunks.
    For chat logs, preserve line structure where possible.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        separators=["\n\n", "\n", "。", ".", "！", "!", "？", "?", " ", ""],
    )
    return splitter.split_text(text)


def parse_chat_log(raw_text: str) -> list[dict]:
    """
    Parse a WeChat/QQ-style chat log and extract messages.

    Expected format (WeChat export):
    2024-01-01 12:00 用户名
    message text
    """
    import re
    lines = raw_text.split("\n")
    messages = []
    current_sender = None
    current_msg = []

    header_pattern = re.compile(
        r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}\s+\d{1,2}:\d{2}(?::\d{2})?\s+(.+)"
    )

    for line in lines:
        m = header_pattern.match(line.strip())
        if m:
            if current_msg and current_sender:
                messages.append({
                    "sender": current_sender.strip(),
                    "content": "\n".join(current_msg).strip(),
                })
            current_sender = m.group(1).strip().strip("'\"")
            current_msg = []
        else:
            if line.strip():
                current_msg.append(line.strip())

    if current_msg and current_sender:
        messages.append({
            "sender": current_sender.strip(),
            "content": "\n".join(current_msg).strip(),
        })

    return messages


def extract_target_only(raw_text: str, target_name: str) -> str:
    """
    Extract only the target person's messages for embedding.
    """
    all_msgs = parse_chat_log(raw_text)
    target_msgs = [m["content"] for m in all_msgs if m["sender"] == target_name]
    return "\n\n".join(target_msgs)

def extract_target_with_context(
    raw_text: str,
    target_name: str,
    max_context_len: int = 120,
) -> str:
    """提取目标人物的消息，并为每条附上「最近一条用户发言」作为语境。

    聊天记录的语境就在相邻对话里，机械拼接即可拿到，不需要 LLM 生成。
    连续发多条时，语境一直沿用，直到用户再次发言。
    """
    msgs = parse_chat_log(raw_text)
    last_user = ""
    units: list[str] = []

    for msg in msgs:
        if msg["sender"] != target_name:
            last_user = msg["content"].strip()[:max_context_len]
            continue

        content = msg["content"].strip()
        if not content:
            continue

        if last_user:
            units.append(f"【用户说】{last_user}\n【{target_name}回复】{content}")
        else:
            units.append(content)

    return "\n\n".join(units)
