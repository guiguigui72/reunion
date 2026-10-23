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
