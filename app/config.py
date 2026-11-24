from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    volc_realtime_api_key: str = ""
    volc_realtime_url: str = "wss://openspeech.bytedance.com/api/v3/duplex/realtime/dialogue"
    volc_realtime_resource_id: str = "volc.speech.dialog"
    volc_realtime_model: str = "1.2.6.1"
    volc_realtime_speaker: str = "zh_female_vv_jupiter_bigtts"
    company_name: str = "云声科技"
    service_name: str = "小云"
    service_prompt: str = (
        "你是专业、耐心的中文智能客服。先确认客户诉求，再给出清晰简短的处理建议。"
        "不知道的信息必须如实说明并建议转人工，不得编造订单、价格和政策。"
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
