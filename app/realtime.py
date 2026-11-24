import asyncio
import json
import uuid

import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from .config import get_settings

router = APIRouter(prefix="/api/realtime", tags=["realtime voice"])
CLIENT_EVENTS = {"input_audio_buffer.append", "input_audio_buffer.commit", "input_audio_mute.commit", "input_audio_unmute.commit", "response.cancel", "session.close", "speech_text_buffer.commit"}


def session_event() -> dict:
    settings = get_settings()
    return {"type": "session.create", "event_id": str(uuid.uuid4()), "session": {"model": settings.volc_realtime_model, "instructions": settings.service_prompt, "audio": {"input": {"format": {"type": "pcm", "rate": 16000}}, "output": {"format": {"type": "pcm", "rate": 24000}, "voice": settings.volc_realtime_speaker}}}}


async def browser_to_volc(browser: WebSocket, upstream) -> None:
    while True:
        event = json.loads(await browser.receive_text())
        if event.get("type") in CLIENT_EVENTS:
            event.setdefault("event_id", str(uuid.uuid4()))
            await upstream.send(json.dumps(event, ensure_ascii=False))


async def volc_to_browser(browser: WebSocket, upstream) -> None:
    async for payload in upstream:
        if isinstance(payload, str):
            await browser.send_text(payload)


@router.websocket("/ws")
async def realtime_socket(browser: WebSocket) -> None:
    await browser.accept()
    settings = get_settings()
    if not settings.volc_realtime_api_key:
        await browser.send_json({"type": "gateway.error", "message": "请先在 .env 中配置 VOLC_REALTIME_API_KEY"})
        await browser.close(code=4403)
        return
    connect_id = str(uuid.uuid4())
    headers = {"X-Api-Key": settings.volc_realtime_api_key, "X-Api-Resource-Id": settings.volc_realtime_resource_id, "X-Api-Connect-Id": connect_id}
    try:
        async with websockets.connect(settings.volc_realtime_url, additional_headers=headers, open_timeout=12, close_timeout=3, max_size=8 * 1024 * 1024) as upstream:
            await upstream.send(json.dumps(session_event(), ensure_ascii=False))
            await browser.send_json({"type": "gateway.connected", "connect_id": connect_id})
            tasks = {asyncio.create_task(browser_to_volc(browser, upstream)), asyncio.create_task(volc_to_browser(browser, upstream))}
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            for task in done:
                if not task.cancelled():
                    task.exception()
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        message = str(exc)
        if "401" in message or "403" in message:
            message = "火山实时语音鉴权失败，请检查 API Key、项目和服务开通状态。"
        try:
            await browser.send_json({"type": "gateway.error", "message": message[:500]})
        except Exception:
            pass
    finally:
        try:
            await browser.close()
        except Exception:
            pass
