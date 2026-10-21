from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import save_config, load_config
from rag.chunker import chunk_text, extract_target_with_context
from rag.embedder import embed_texts
from rag.store import reset_collection
from persona.distiller import distill_persona, extract_entities, merge_answers

router = APIRouter()


class SetupRequest(BaseModel):
    api_key: str
    name: str
    your_name: str = ""
    relationship: str = ""
    personality: str = ""
    extra: str = ""
    last_seen: str = ""
    birth_info: str = ""
    chat_log: str = ""


class AnswerItem(BaseModel):
    entity: str
    type: str = ""
    detail: str = ""
    context_hint: str = ""


class AnswersRequest(BaseModel):
    api_key: str
    answers: list[AnswerItem]


@router.post("/api/setup")
async def setup(req: SetupRequest):
    if not req.api_key or not req.name:
        raise HTTPException(status_code=400, detail="api_key and name are required")

    # Save config, preserving avatar if already set
    existing = load_config()
    save_config({
        "api_key": req.api_key,
        "name": req.name,
        "your_name": req.your_name,
        "relationship": req.relationship,
        "personality": req.personality,
        "extra": req.extra,
        "last_seen": req.last_seen,
        "birth_info": req.birth_info,
        "has_avatar": existing.get("has_avatar", False),
    })

    # Distill persona
    persona = ""
    if req.chat_log.strip():
        try:
            persona = distill_persona(
                chat_log=req.chat_log,
                name=req.name,
                relationship=req.relationship,
                personality=req.personality,
                extra=req.extra,
                last_seen=req.last_seen,
                birth_info=req.birth_info,
                api_key=req.api_key,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"人格蒸馏失败: {str(e)}")

            # Chunk and embed target's messages
        try:
            target_text = extract_target_with_context(req.chat_log, req.name)
            if not target_text.strip():
                raise HTTPException(
                    status_code=400,
                    detail=f"这份聊天记录里没有找到「{req.name}」说的话，是不是导出时少选了什么？",
                )
            chunks = chunk_text(target_text)
            embeddings = embed_texts(chunks)
            collection = reset_collection("memories")
            collection.add(
                documents=chunks,
                embeddings=embeddings,
                ids=[f"mem_{i}" for i in range(len(chunks))],
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"记忆索引失败: {str(e)}")

    # Extract entities for smart follow-up
    questions = []
    if req.chat_log.strip():
        try:
            questions = extract_entities(req.chat_log, req.api_key)
        except Exception:
            questions = []

    return {
        "status": "ok",
        "message": "设置完成",
        "has_persona": bool(persona),
        "questions": questions,
    }


@router.post("/api/setup/answers")
async def submit_answers(req: AnswersRequest):
    if not req.api_key or not req.answers:
        raise HTTPException(status_code=400, detail="api_key and answers are required")

    try:
        answers = [a.model_dump() for a in req.answers]
        merge_answers(answers, req.api_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"答案合并失败: {str(e)}")

    return {"status": "ok"}
