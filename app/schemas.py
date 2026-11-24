from typing import Literal

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    messages: list[Message] = Field(min_length=1, max_length=30)


class LeaveParseRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


class SalesTurnRequest(BaseModel):
    audio_base64: str = Field(min_length=1)
    history: list[Message] = Field(default_factory=list, max_length=20)


class SalesSpeakRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
