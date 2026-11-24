from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .realtime import router

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
app = FastAPI(title="云声实时语音客服", version="2.0.0")
app.include_router(router)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "realtime.html")


@app.get("/api/health")
async def health() -> dict[str, str | bool]:
    settings = get_settings()
    return {"status": "ok", "configured": bool(settings.volc_realtime_api_key), "provider": "volcengine-seeduplex"}


@app.get("/api/config")
async def public_config() -> dict[str, str | bool]:
    settings = get_settings()
    return {"companyName": settings.company_name, "serviceName": settings.service_name, "configured": bool(settings.volc_realtime_api_key), "model": settings.volc_realtime_model, "speaker": settings.volc_realtime_speaker}
