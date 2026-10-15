from openai import OpenAI

from config import PERSONA_PATH, load_config
from rag.embedder import embed_texts
from rag.store import query_collection
from persona.correction import handle_correction, is_correction_intent
from chat.history import get_history

GUARDRAIL = """
## 重要规则
- 绝不编造不存在的记忆、经历或事实。
- 用自然、口语化的方式回应，就像日常聊天一样。
"""

MEMORY_GUARDRAIL = """
## 关于下方「记忆片段」
这些片段是从真实聊天记录中检索出来的相关往事。
- 提到过去的事时，只依据这些片段，不要补充片段里没有的细节。
- 如果用户问起的事不在片段中，就坦诚地说「记不太清了」或「我好像想不起来了」。
"""


def build_system_prompt(persona: str, memories: list[str]) -> str:
    """组装 System Prompt。

    记忆段只在真的检索到记忆时才拼接 —— 约束只在它的前提成立时才生效。
    """
    if not memories:
        return f"{persona}\n\n{GUARDRAIL}"

    memory_text = "\n".join(f"- {m}" for m in memories)
    return f"{persona}\n\n{GUARDRAIL}\n\n{MEMORY_GUARDRAIL}\n\n## 记忆片段\n{memory_text}"


def classify_intent(user_message: str, api_key: str) -> dict:
    """
    Use LLM to decide: is this a correction, a regular message,
    or something that needs memory search?

    Returns: {"type": "correction"|"chat"|"memory_search", "query": str|None}
    """
    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")

    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": (
                "Classify this user message in a chat with their AI companion "
                "that mimics a deceased loved one. Reply with ONLY one word:\n"
                "- 'correction' if user is saying the AI doesn't sound like the person\n"
                "- 'memory_search' if the message asks about past events/memories\n"
                "- 'chat' if it's casual conversation (greetings, feelings, daily chat)\n\n"
                "Examples:\n"
                "'他才不会这么说' -> correction\n"
                "'你还记得我们去海边那次吗' -> memory_search\n"
                "'今天好累啊' -> chat"
            )},
            {"role": "user", "content": user_message},
        ],
        max_tokens=10,
        temperature=0.0,
    )
    result = resp.choices[0].message.content.strip().lower()

    query = None
    intent_type = "chat"
    if "correction" in result:
        intent_type = "correction"
    elif "memory" in result:
        intent_type = "memory_search"
        query = user_message

    return {"type": intent_type, "query": query}


def chat(user_message: str, api_key: str) -> str:
    """
    Main agent loop entry point.

    1. Check for correction intent
    2. If normal: decide memory search needed? -> search -> build prompt -> reply
    """
    config = load_config()

    # Check correction
    if is_correction_intent(user_message):
        return handle_correction(user_message, api_key)

    # Classify intent via LLM
    intent = classify_intent(user_message, api_key)

    if intent["type"] == "correction":
        return handle_correction(user_message, api_key)

    # Load persona
    persona = ""
    if PERSONA_PATH.exists():
        persona = PERSONA_PATH.read_text(encoding="utf-8")

    # Memory search
    memories = []
    if intent["type"] == "memory_search":
        query_embedding = embed_texts([user_message])[0]
        memories = query_collection(query_embedding, n_results=5)

    # Build prompt and call LLM
    system_prompt = build_system_prompt(persona, memories)

    # Include recent conversation history for context
    recent_history = get_history(limit=30)
    messages = [{"role": "system", "content": system_prompt}]
    for h in recent_history:
        messages.append({"role": h["role"], "content": h["content"]})
    messages.append({"role": "user", "content": user_message})

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")

    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=messages,
        temperature=0.7,
        max_tokens=1024,
    )

    return resp.choices[0].message.content
