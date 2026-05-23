from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel


class LLMConfig(BaseModel):
    provider: Literal["ollama", "openai_compat"] = "ollama"
    model: str = "llama3.2"

    # Ollama-specific
    ollama_host: str = "http://localhost:11434"

    # OpenAI-compatible (Groq, OpenRouter, etc.)
    api_base: str = "https://api.groq.com/openai/v1"
    api_key: str = ""
    max_retries: int = 3


class Config(BaseModel):
    llm: LLMConfig = LLMConfig()
    state_db_path: Path = Path("~/.autoflow/state.db")
    workflows_dir: Path = Path("~/.autoflow/workflows")

    @classmethod
    def from_env(cls) -> Config:
        return cls(
            llm=LLMConfig(
                provider=os.getenv("AUTOFLOW_LLM_PROVIDER", "ollama"),  # type: ignore
                model=os.getenv("AUTOFLOW_LLM_MODEL", "llama3.2"),
                ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
                api_base=os.getenv("AUTOFLOW_API_BASE", "https://api.groq.com/openai/v1"),
                api_key=os.getenv("AUTOFLOW_API_KEY", ""),
            ),
        )
