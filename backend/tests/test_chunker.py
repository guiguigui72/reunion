from rag.chunker import extract_target_only, parse_chat_log


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