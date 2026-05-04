from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import save_config, load_config
from rag.chunker import chunk_text, extract_target_only
from rag.embedder import embed_texts
from rag.store import get_or_create_collection
from persona.distiller import distill_persona

router = APIRouter()


class SetupRequest(BaseModel):
    api_key: str
    name: str
    your_name: str = ""
    relationship: str = ""
    personality: str = ""
    extra: str = ""
    chat_log: str = ""


@router.post("/api/setup")
async def setup(req: SetupRequest):
    if not req.api_key or not req.name:
        raise HTTPException(status_code=400, detail="api_key and name are required")

    # Save config first
    save_config({
        "api_key": req.api_key,
        "name": req.name,
        "your_name": req.your_name,
        "relationship": req.relationship,
        "personality": req.personality,
        "extra": req.extra,
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
                api_key=req.api_key,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"人格蒸馏失败: {str(e)}")

        # Chunk and embed target's messages
        try:
            target_text = extract_target_only(req.chat_log, req.name)
            if target_text.strip():
                chunks = chunk_text(target_text)
                embeddings = embed_texts(chunks)
                collection = get_or_create_collection("memories")
                collection.add(
                    documents=chunks,
                    embeddings=embeddings,
                    ids=[f"mem_{i}" for i in range(len(chunks))],
                )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"记忆索引失败: {str(e)}")

    return {
        "status": "ok",
        "message": "设置完成",
        "has_persona": bool(persona),
    }
