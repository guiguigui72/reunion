from rag.chunker import (
    extract_target_only,
    extract_target_with_context,
    parse_chat_log,
)


def test_parse_chat_log_strips_quoted_sender_names():
    """真实微信导出里，发言人常被包在引号里：'妈妈'。"""
    raw = "2024-01-01 10:00 '妈妈'\n最近好吗\n"
    msgs = parse_chat_log(raw)
    assert msgs[0]["sender"] == "妈妈"


def test_extract_target_only_matches_name_from_wizard():
    """用户在引导页填「妈妈」，应该能匹配导出里的 '妈妈'。"""
    raw = (
        "2024-01-01 10:00 '妈妈'\n最近好吗\n"
        "2024-01-01 10:01 '我'\n挺好的\n"
    )
    assert extract_target_only(raw, "妈妈") == "最近好吗"


def test_unquoted_names_still_work():
    """不带引号的格式不能被改坏。"""
    raw = "2024-01-01 10:00 妈妈\n最近好吗\n"
    assert parse_chat_log(raw)[0]["sender"] == "妈妈"


def test_context_carried_across_consecutive_replies():
    """连发多条时，语境沿用同一条用户提问。"""
    chat = (
        "2024-01-01 10:00 '我'\n你还记得去北京那次吗\n"
        "2024-01-01 10:01 '妈妈'\n记得啊\n"
        "2024-01-01 10:02 '妈妈'\n那天特别冷\n"
    )
    out = extract_target_with_context(chat, "妈妈")
    assert out.count("你还记得去北京那次吗") == 2


def test_new_user_message_updates_context():
    """用户再开口时，语境切换。"""
    chat = (
        "2024-01-01 10:00 '我'\n第一件事\n"
        "2024-01-01 10:01 '妈妈'\n回复一\n"
        "2024-01-01 10:02 '我'\n第二件事\n"
        "2024-01-01 10:03 '妈妈'\n回复二\n"
    )
    out = extract_target_with_context(chat, "妈妈")
    first_block, second_block = out.split("\n\n")
    assert "第一件事" in first_block and "回复一" in first_block
    assert "第二件事" in second_block and "回复二" in second_block


def test_target_speaking_first_has_no_empty_context():
    """目标人物先开口时，不该拼出空的【用户说】。"""
    chat = "2024-01-01 10:00 '妈妈'\n我先说一句\n"
    assert extract_target_with_context(chat, "妈妈") == "我先说一句"


def test_context_is_truncated():
    """超长用户消息必须截断，否则会灌满很多块。"""
    long_user = "啊" * 300
    chat = (
        f"2024-01-01 10:00 '我'\n{long_user}\n"
        "2024-01-01 10:01 '妈妈'\n回复内容\n"
    )
    out = extract_target_with_context(chat, "妈妈")
    assert "啊" * 120 in out
    assert "啊" * 121 not in out