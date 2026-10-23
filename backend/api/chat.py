from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from config import load_config
from agent.loop import chat as agent_chat
from chat.history import save_message, get_history

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    history: list[dict]


@router.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    config = load_config()
    api_key = config.get("api_key", "")
    if not api_key:
        raise HTTPException(status_code=400, detail="请先设置 API Key")

    if not req.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")

    save_message("user", req.message)

    try:
        # agent_chat 内部是阻塞调用（等 DeepSeek 返回），必须移出事件循环，
        # 否则等待期间健康检查、历史等请求全部排队
        reply = await run_in_threadpool(agent_chat, req.message, api_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"对话失败: {str(e)}")

    save_message("assistant", reply)

    return ChatResponse(
        reply=reply,
        history=get_history(50),
    )


@router.get("/api/chat/history")
async def chat_history():
    return {"history": get_history(50)}
