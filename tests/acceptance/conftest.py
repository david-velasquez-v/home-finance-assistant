from pathlib import Path
import instructor
import pytest

from expenses.config import Settings
from expenses.external.llm import build_client


_API_KEY_FIELDS = {
    "anthropic": "anthropic_api_key",
    "openai": "openai_api_key",
    "google": "gemini_api_key",
}


@pytest.fixture(scope="session")
def acceptance_settings() -> Settings:
    current_file_path = Path(__file__).resolve()
    two_folders_up = current_file_path.parents[2]
    env_path = two_folders_up / ".env.test"

    # Check if the file exists
    assert env_path.is_file(), f"File not found: {env_path}"
    
    settings = Settings(_env_file=env_path)  # ty: ignore -- reads from .env at runtime
    field: str | None = _API_KEY_FIELDS.get(settings.llm_provider)
    if field is None or not getattr(settings, field, ""):
        pytest.skip(f"no API key configured for provider {settings.llm_provider!r}")
    return settings


@pytest.fixture(scope="session")
def client(acceptance_settings: Settings) -> instructor.Instructor:
    return build_client(config=acceptance_settings)
