import instructor

from expenses.config import Settings


def build_client(config: Settings) -> instructor.Instructor:
    return instructor.from_provider(
        model=f"{config.llm_provider}/{config.llm_model}",
        api_key=_api_key_for(config),
    )


def _api_key_for(config: Settings) -> str:
    match config.llm_provider:
        case "anthropic":
            return config.anthropic_api_key
        case "openai":
            return config.openai_api_key
        case "google":
            return config.gemini_api_key
