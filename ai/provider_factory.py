from __future__ import annotations

import os
from typing import Optional

from .providers.base import AiProvider
from .providers.openai_provider import OpenAiProvider


def get_provider() -> AiProvider:
    provider = os.environ.get("AI_PROVIDER", "openai").lower()
    if provider == "lmstudio":
        from .providers.lmstudio_provider import LmStudioProvider

        return LmStudioProvider(
            base_url=os.environ.get("LM_STUDIO_BASE_URL", "http://localhost:1234/v1"),
            model=os.environ.get("LM_STUDIO_MODEL", "qwen2.5:3b"),
        )
    # default to openai
    return OpenAiProvider()


