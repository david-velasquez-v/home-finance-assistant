from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    telegram_bot_token: str
    telegram_user_david: int
    telegram_user_daniela: int

    llm_provider: Literal["anthropic", "openai", "google"] = "anthropic"
    llm_model: str = "claude-haiku-4-5-20251001"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""

    google_spreadsheet_id: str
    google_sheet_name: str = "Gastos"
    credentials_path: Path = Path("credentials/service_account.json")

    webhook_host: str = "0.0.0.0"
    webhook_port: int = 8080
    webhook_secret: str = ""
