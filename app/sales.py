import base64

import httpx
from fastapi import APIRouter, HTTPException

from .config import get_settings
from .schemas import SalesSpeakRequest, SalesTurnRequest
from .speech import recognize_pcm, synthesize_mp3

router = APIRouter(prefix="/api/sales", tags=["AI sales"])
WELCOME = "您好，我是云声 AI 产品顾问，本次由智能语音助手为您服务。请问现在方便用一分钟了解一下 iPhone 17 吗？"


def require_config():
    settings = get_settings()
    values = {"ARK_API_KEY": settings.ark_api_key, "ARK_MODEL_ENDPOINT_ID": settings.ark_model_endpoint_id, "VOLC_SPEECH_APP_ID": settings.volc_speech_app_id, "VOLC_SPEECH_ACCESS_TOKEN": settings.volc_speech_access_token, "VOLC_ASR_RESOURCE_ID": settings.volc_asr_resource_id, "VOLC_TTS_RESOURCE_ID": settings.volc_tts_resource_id, "VOLC_TTS_VOICE_TYPE": settings.volc_tts_voice_type}
    missing = [key for key, value in values.items() if not value]
    if missing:
        raise HTTPException(503, detail="缺少配置：" + ", ".join(missing))
    return settings


async def generate_reply(customer: str, history, settings) -> str:
    facts = "iPhone 17官方信息：256GB 5999元起，512GB 7999元；6.3英寸OLED超视网膜XDR屏，ProMotion最高120Hz和全天候显示；A19芯片；4800万像素融合式双摄；1800万像素Center Stage前置摄像头；视频播放最长30小时。"
    rules = "你是云声AI产品顾问。已披露AI身份。仅在客户明确同意后推荐；如表示不方便、不需要、拒绝或别再联系，礼貌结束并在末尾写[END_CALL]。每次最多两句话，先回答再推荐一个相关卖点，不施压，不虚构优惠、库存、赠品或保修。"
    messages = [{"role": "system", "content": rules + facts}]
    messages.extend(item.model_dump() for item in history[-12:])
    messages.append({"role": "user", "content": customer})
    async with httpx.AsyncClient(timeout=12) as client:
        response = await client.post(f"{settings.ark_base_url.rstrip('/')}/chat/completions", headers={"Authorization": f"Bearer {settings.ark_api_key}"}, json={"model": settings.ark_model_endpoint_id, "messages": messages, "temperature": 0.2, "thinking": {"type": "disabled"}, "max_tokens": 180})
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()


@router.get("/config")
async def config():
    settings = get_settings()
    fields = [settings.ark_api_key, settings.ark_model_endpoint_id, settings.volc_speech_app_id, settings.volc_speech_access_token, settings.volc_asr_resource_id, settings.volc_tts_resource_id, settings.volc_tts_voice_type]
    return {"configured": all(fields), "welcome": WELCOME}


@router.post("/speak")
async def speak(request: SalesSpeakRequest):
    settings = require_config()
    try:
        audio = await synthesize_mp3(request.text, settings)
        return {"audioBase64": base64.b64encode(audio).decode(), "mimeType": "audio/mpeg"}
    except Exception as exc:
        raise HTTPException(502, detail=f"语音合成失败：{exc}") from exc


@router.post("/turn")
async def turn(request: SalesTurnRequest):
    settings = require_config()
    try:
        customer = await recognize_pcm(base64.b64decode(request.audio_base64), settings)
        if not customer:
            raise RuntimeError("没有识别到有效语音")
        reply = await generate_reply(customer, request.history, settings)
        clean = reply.replace("[END_CALL]", "").strip()
        audio = await synthesize_mp3(clean, settings)
        return {"customerText": customer, "replyText": clean, "endCall": "[END_CALL]" in reply, "audioBase64": base64.b64encode(audio).decode(), "mimeType": "audio/mpeg"}
    except Exception as exc:
        raise HTTPException(502, detail=f"AI 对话失败：{exc}") from exc
