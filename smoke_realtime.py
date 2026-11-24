"""Connect to the local gateway, verify the upstream session, then close cleanly."""
import asyncio
import json

import websockets


async def main() -> None:
    async with websockets.connect("ws://127.0.0.1:8000/api/realtime/ws", open_timeout=10) as ws:
        for _ in range(8):
            event = json.loads(await asyncio.wait_for(ws.recv(), timeout=15))
            event_type = event.get("type", "unknown")
            print(event_type)
            if event_type == "session.created":
                await ws.send(json.dumps({"type": "session.close"}))
            if event_type == "session.closed":
                return
            if event_type in {"error", "gateway.error"}:
                message = event.get("message") or event.get("error", {}).get("message") or "unknown error"
                raise RuntimeError(message)
    raise RuntimeError("session did not reach session.closed")


if __name__ == "__main__":
    asyncio.run(main())
