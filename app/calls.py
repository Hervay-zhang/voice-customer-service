import asyncio
import os
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

router = APIRouter(prefix="/api/calls", tags=["calls"])
connections: dict[str, WebSocket] = {}
push_tokens: dict[str, str] = {}


class DeviceRegistration(BaseModel):
    device_id: str
    push_token: str


@router.post("/devices")
async def register_device(data: DeviceRegistration) -> dict[str, bool]:
    push_tokens[data.device_id] = data.push_token
    return {"registered": True}


@router.get("/devices/{device_id}")
async def device_status(device_id: str) -> dict[str, bool]:
    return {"online": device_id in connections, "pushReady": device_id in push_tokens}


async def send_push(device_id: str, caller_id: str) -> None:
    """Send an FCM data notification when Firebase credentials are configured."""
    token = push_tokens.get(device_id)
    credentials = os.getenv("FIREBASE_CREDENTIALS", "")
    if not token or not credentials:
        return
    try:
        import firebase_admin
        from firebase_admin import credentials as firebase_credentials, messaging

        if not firebase_admin._apps:
            firebase_admin.initialize_app(firebase_credentials.Certificate(credentials))
        message = messaging.Message(
            token=token,
            data={"type": "incoming_call", "callerId": caller_id, "deviceId": device_id},
            android=messaging.AndroidConfig(priority="high"),
        )
        await asyncio.to_thread(messaging.send, message)
    except Exception:
        # A live websocket still carries the call; push setup errors must not break it.
        return


@router.websocket("/ws/{client_id}")
async def signaling_socket(websocket: WebSocket, client_id: str) -> None:
    await websocket.accept()
    old = connections.get(client_id)
    if old:
        await old.close(code=4001)
    connections[client_id] = websocket
    try:
        await websocket.send_json({"type": "ready", "clientId": client_id})
        while True:
            message: dict[str, Any] = await websocket.receive_json()
            target_id = str(message.get("target", ""))
            if not target_id:
                continue
            outgoing = {**message, "from": client_id}
            target = connections.get(target_id)
            if target:
                await target.send_json(outgoing)
            else:
                await websocket.send_json({"type": "unavailable", "target": target_id})
            if message.get("type") == "offer":
                await send_push(target_id, client_id)
    except WebSocketDisconnect:
        pass
    finally:
        if connections.get(client_id) is websocket:
            connections.pop(client_id, None)
