"""LLM initialization and provider abstraction."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI


Provider = Literal["openai", "anthropic"]


@dataclass
class LLMService:
    provider: Provider = "openai"
    model: str = "gpt-4o-mini"
    temperature: float = 0.2

    def create_chat_model(self) -> BaseChatModel:
        load_dotenv()
        provider = os.getenv("LLM_PROVIDER", self.provider).lower()
        model = os.getenv("OPENAI_MODEL", self.model)

        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OPENAI_API_KEY is required to run the analysis pipeline.")
            return ChatOpenAI(
                api_key=api_key,
                model=model,
                temperature=self.temperature,
            )

        if provider == "anthropic":
            raise NotImplementedError(
                "Anthropic provider placeholder exists for swap-readiness. "
                "Install and wire langchain-anthropic to enable it."
            )

        raise ValueError(f"Unsupported LLM provider: {provider}")
