import gzip
import json
import struct
import uuid

import websockets

from .config import Settings


def _header(message_type: int, flags: int, serialization: int, compression: int) -> bytes:
    return bytes([0x11, (message_type << 4) | flags, (serialization << 4) | compression, 0])


def _packet(header: bytes, payload: bytes, sequence: int | None = None) -> bytes:
    prefix = struct.pack(">i", sequence) if sequence is not None else b""
    return header + prefix + struct.pack(">I", len(payload)) + payload


async def recognize_pcm(pcm: bytes, settings: Settings) -> str:
    headers = {
        "X-Api-App-Key": settings.volc_speech_app_id,
        "X-Api-Access-Key": settings.volc_speech_access_token,
        "X-Api-Resource-Id": settings.volc_asr_resource_id,
        "X-Api-Request-Id": str(uuid.uuid4()),
    }
    config = {
        "user": {"uid": "yunsheng-sales"},
        "audio": {"format": "pcm", "codec": "raw", "rate": 16000, "bits": 16, "channel": 1},
        "request": {"model_name": "bigmodel", "enable_itn": True, "enable_punc": True, "show_utterances": True, "result_type": "full"},
    }
    async with websockets.connect("wss://openspeech.bytedance.com/api/v3/sauc/bigmodel_nostream", additional_headers=headers, open_timeout=8, close_timeout=2) as ws:
        # The v3 ASR service counts the full client request as sequence 1.
        await ws.send(_packet(_header(1, 1, 1, 1), gzip.compress(json.dumps(config, ensure_ascii=False).encode()), 1))
        size = 6400
        sequence = 2
        for offset in range(0, len(pcm), size):
            last = offset + size >= len(pcm)
            chunk = gzip.compress(pcm[offset:offset + size])
            await ws.send(_packet(_header(2, 3 if last else 1, 0, 1), chunk, -sequence if last else sequence))
            sequence += 1
        transcript = ""
        while True:
            try:
                raw = await ws.recv()
            except websockets.exceptions.ConnectionClosedOK:
                return transcript.strip()
            if not isinstance(raw, bytes) or len(raw) < 8:
                continue
            kind, flags, compression, offset = raw[1] >> 4, raw[1] & 15, raw[2] & 15, 4
            seq = None
            if flags in (1, 2, 3):
                seq = struct.unpack(">i", raw[offset:offset + 4])[0]
                offset += 4
            length = struct.unpack(">I", raw[offset:offset + 4])[0]
            body = raw[offset + 4:offset + 4 + length]
            if compression == 1:
                body = gzip.decompress(body)
            if kind == 15:
                raise RuntimeError(body.decode(errors="replace"))
            if kind == 9:
                data = json.loads(body)
                transcript = data.get("result", data).get("text", transcript)
                if seq is not None and seq < 0:
                    return transcript.strip()


async def synthesize_mp3(text: str, settings: Settings) -> bytes:
    request = {
        "app": {"appid": settings.volc_speech_app_id, "token": settings.volc_speech_access_token, "cluster": settings.volc_tts_resource_id or "volcano_tts"},
        "user": {"uid": "yunsheng-sales"},
        "audio": {"voice_type": settings.volc_tts_voice_type, "encoding": "mp3", "speed_ratio": 1.0, "volume_ratio": 1.0, "pitch_ratio": 1.0},
        "request": {"reqid": str(uuid.uuid4()), "text": text, "text_type": "plain", "operation": "submit"},
    }
    payload = gzip.compress(json.dumps(request, ensure_ascii=False).encode())
    audio = bytearray()
    async with websockets.connect("wss://openspeech.bytedance.com/api/v1/tts/ws_binary", additional_headers={"Authorization": f"Bearer; {settings.volc_speech_access_token}"}, open_timeout=8, close_timeout=2) as ws:
        await ws.send(_packet(_header(1, 0, 1, 1), payload))
        while True:
            raw = await ws.recv()
            if not isinstance(raw, bytes) or len(raw) < 4:
                continue
            kind, flags, offset = raw[1] >> 4, raw[1] & 15, 4
            if kind == 11:
                if flags not in (1, 2, 3) or len(raw) < offset + 8:
                    continue
                seq = struct.unpack(">i", raw[offset:offset + 4])[0]
                length = struct.unpack(">I", raw[offset + 4:offset + 8])[0]
                if len(raw) < offset + 8 + length:
                    raise RuntimeError("TTS 返回了不完整的音频帧")
                audio.extend(raw[offset + 8:offset + 8 + length])
                if seq < 0:
                    return bytes(audio)
            elif kind == 15:
                if len(raw) < offset + 8:
                    raise RuntimeError("TTS 返回了无法解析的错误帧")
                code = struct.unpack(">I", raw[offset:offset + 4])[0]
                length = struct.unpack(">I", raw[offset + 4:offset + 8])[0]
                body = raw[offset + 8:offset + 8 + length]
                if (raw[2] & 15) == 1:
                    body = gzip.decompress(body)
                raise RuntimeError(f"TTS {code}: {body.decode(errors='replace')}")
            elif kind == 12:
                # Frontend/control responses do not carry audio sequence fields.
                continue
