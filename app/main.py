import json
from collections.abc import AsyncIterator
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .calls import router as calls_router
from .sales import router as sales_router
from .schemas import ChatRequest, LeaveParseRequest

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="云声智能客服", version="1.0.0")
app.include_router(calls_router)
app.include_router(sales_router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/leave", include_in_schema=False)
async def leave_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "leave.html")


@app.get("/call", include_in_schema=False)
async def call_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "call.html")


@app.get("/mobile", include_in_schema=False)
async def mobile_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "mobile.html")


@app.get("/api/config")
async def public_config() -> dict[str, str | bool]:
    settings = get_settings()
    return {
        "companyName": settings.company_name,
        "serviceName": settings.service_name,
        "configured": bool(settings.ark_api_key and settings.ark_model_endpoint_id),
    }


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat")
async def chat(payload: ChatRequest) -> StreamingResponse:
    settings = get_settings()
    if not settings.ark_api_key or not settings.ark_model_endpoint_id:
        raise HTTPException(status_code=503, detail="请先在 .env 中配置火山方舟 API Key 和推理接入点 ID")

    system_prompt = (
        f"你是{settings.company_name}的智能语音客服{settings.service_name}。"
        "请用简洁、自然、有耐心的中文回答。优先确认用户诉求，再提供明确步骤。"
        "不知道的信息要如实说明并建议转人工，不得编造政策、价格或订单状态。"
        "回答适合被语音朗读，避免复杂表格、Markdown 标记和冗长段落。"
    )
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(message.model_dump() for message in payload.messages)

    async def generate() -> AsyncIterator[str]:
        url = f"{settings.ark_base_url.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {settings.ark_api_key}"}
        body = {
            "model": settings.ark_model_endpoint_id,
            "messages": messages,
            "stream": True,
            "temperature": 0.4,
        }
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                async with client.stream("POST", url, headers=headers, json=body) as response:
                    if response.status_code >= 400:
                        detail = (await response.aread()).decode("utf-8", errors="replace")
                        yield json.dumps({"error": f"方舟请求失败：{detail[:300]}"}, ensure_ascii=False) + "\n"
                        return
                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            text = chunk["choices"][0]["delta"].get("content", "")
                            if text:
                                yield json.dumps({"text": text}, ensure_ascii=False) + "\n"
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
        except httpx.HTTPError as exc:
            yield json.dumps({"error": f"无法连接火山方舟：{exc}"}, ensure_ascii=False) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")


@app.post("/api/leave/parse")
async def parse_leave(payload: LeaveParseRequest) -> dict:
    """Turn a natural-language leave request into editable form fields."""
    settings = get_settings()
    if not settings.ark_api_key or not settings.ark_model_endpoint_id:
        raise HTTPException(status_code=503, detail="火山方舟尚未配置")

    prompt = f"""今天日期是 {__import__('datetime').date.today().isoformat()}。
请从下面的中文请假描述中提取信息，只返回一个 JSON 对象，不要 Markdown：
{{"leaveType":"事假|病假|年假|调休|婚假|产假|陪产假|其他","startDate":"YYYY-MM-DD或空字符串","endDate":"YYYY-MM-DD或空字符串","period":"全天|上午|下午","reason":"简洁原因","confidence":0到1}}
日期必须严格按日历计算，不得自行猜测日期。相对日期规则：
1. 如果用户只说“下周”而没有指定星期几，开始日期固定为下周一；
2. “请一周”固定表示连续 7 个自然日，结束日期为开始日期加 6 天；
3. “下周一”等指定星期时，以指定日期作为开始日期；
4. 如果只说一天，开始和结束日期相同；“明天”“后天”等按今天日期换算；
5. “回家结婚”“本人结婚”应识别为婚假。
未提及且无法可靠推断的字段使用空字符串，period 默认全天。
请假描述：{payload.text}"""
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(8.0, connect=3.0)) as client:
            response = await client.post(
                f"{settings.ark_base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {settings.ark_api_key}"},
                json={
                    "model": settings.ark_model_endpoint_id,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                    "thinking": {"type": "disabled"},
                    "max_tokens": 220,
                },
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]
            result = json.loads(content)
            return {"source": "ark", **result}
    except (httpx.HTTPError, KeyError, IndexError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail=f"请假信息解析失败：{exc}") from exc
