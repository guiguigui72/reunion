from agent.loop import build_system_prompt

PERSONA = "# 妈妈 — Relationship Persona\n\n说话简短，爱用「嗯」。"


def test_persona_always_present():
    """无论有没有记忆，人格设定都必须出现。"""
    assert PERSONA in build_system_prompt(PERSONA, [])


def test_no_memory_section_when_no_memories():
    """bug #1 回归：没有检索到记忆时，不得出现任何「记忆」相关指令。"""
    prompt = build_system_prompt(PERSONA, [])

    assert "记忆片段" not in prompt
    assert "记不太清了" not in prompt
    assert "暂无相关记忆" not in prompt


def test_memory_section_present_when_memories_exist():
    """检索到记忆时，记忆内容和约束都要出现。"""
    prompt = build_system_prompt(PERSONA, ["用户和妈妈一起去过海边"])

    assert "用户和妈妈一起去过海边" in prompt
    assert "记不太清了" in prompt


def test_never_fabricate_rule_always_present():
    """禁止编造这条约束与记忆无关，必须永远存在。"""
    for memories in ([], ["用户去过海边"]):
        assert "绝不编造" in build_system_prompt(PERSONA, memories)


def test_empty_persona_does_not_crash():
    """用户没走完 setup 就打开聊天窗口时，不该崩。"""
    prompt = build_system_prompt("", [])

    assert isinstance(prompt, str)
    assert "记忆片段" not in prompt