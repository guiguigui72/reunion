import logging
import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse
from pydantic import BaseModel

from config import load_config, save_config, PERSONA_PATH, AVATAR_PATH, DATA_DIR
from persona.distiller import merge_persona

logger = logging.getLogger(__name__)

router = APIRouter()


class SettingsUpdate(BaseModel):
    api_key: str = ""
    name: str = ""
    your_name: str = ""
    relationship: str = ""
    personality: str = ""
    extra: str = ""


@router.get("/api/settings")
async def get_settings():
    config = load_config()
    return {
        "api_key": config.get("api_key", "")[:8] + "****" if config.get("api_key") else "",
        "name": config.get("name", ""),
        "your_name": config.get("your_name", ""),
        "relationship": config.get("relationship", ""),
        "personality": config.get("personality", ""),
        "extra": config.get("extra", ""),
        "has_avatar": config.get("has_avatar", False),
    }


@router.put("/api/settings")
async def update_settings(req: SettingsUpdate):
    config = load_config()
    api_key = req.api_key if req.api_key and "****" not in req.api_key else config.get("api_key", "")

    updated = {}
    if req.name and req.name != config.get("name"):
        updated["name"] = req.name
    if req.personality and req.personality != config.get("personality"):
        updated["personality"] = req.personality
    if req.extra != config.get("extra"):
        updated["extra"] = req.extra
    if req.relationship and req.relationship != config.get("relationship"):
        updated["relationship"] = req.relationship

    # 合并而不是覆盖：保留所有本次未提及的字段
    # （has_avatar / last_seen / birth_info 等）
    merged = dict(config)
    merged["api_key"] = api_key
    for field in ("name", "your_name", "relationship", "personality", "extra"):
        value = getattr(req, field)
        if value:
            merged[field] = value
    save_config(merged)

    if updated and PERSONA_PATH.exists() and api_key:
        try:
            await run_in_threadpool(merge_persona, updated, api_key)
        except Exception:
            logger.exception("人格增量合并失败；设置已保存，但 persona.md 未更新")

    return {"status": "ok"}


@router.delete("/api/settings/reset")
async def reset_all():
    if DATA_DIR.exists():
        shutil.rmtree(str(DATA_DIR))
    return {"status": "ok", "message": "已清除所有数据"}


@router.post("/api/settings/avatar")
async def upload_avatar(file: UploadFile = File(...)):
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="头像文件不能超过5MB")
    AVATAR_PATH.parent.mkdir(parents=True, exist_ok=True)
    AVATAR_PATH.write_bytes(content)
    config = load_config()
    config["has_avatar"] = True
    save_config(config)
    return {"status": "ok"}


@router.get("/api/settings/avatar")
async def get_avatar():
    if AVATAR_PATH.exists():
        return FileResponse(str(AVATAR_PATH), media_type="image/png")
    raise HTTPException(status_code=404, detail="未设置头像")
