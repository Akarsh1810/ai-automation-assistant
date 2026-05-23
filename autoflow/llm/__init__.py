from autoflow.config import Config
from autoflow.llm.base import LLMProvider, LLMResult, ProviderError
from autoflow.llm.ollama import OllamaProvider
from autoflow.llm.openai_compat import OpenAICompatibleProvider


def create_provider(config: Config | None = None) -> LLMProvider:
    cfg = config or Config.from_env()
    if cfg.llm.provider == "ollama":
        return OllamaProvider(model=cfg.llm.model, host=cfg.llm.ollama_host)
    return OpenAICompatibleProvider(
        model=cfg.llm.model,
        api_base=cfg.llm.api_base,
        api_key=cfg.llm.api_key,
        max_retries=cfg.llm.max_retries,
    )


__all__ = [
    "LLMProvider",
    "LLMResult",
    "ProviderError",
    "OllamaProvider",
    "OpenAICompatibleProvider",
    "create_provider",
]
