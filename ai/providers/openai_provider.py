from __future__ import annotations

import os
from dataclasses import dataclass

from .base import AiProvider, GenerateParams


@dataclass
class OpenAiProvider(AiProvider):
    model: str = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    api_key: str = os.environ.get("OPENAI_API_KEY", "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")

    def generate(self, *, system_prompt: str, user_prompt: str, params: GenerateParams) -> str:
        try:
            # Lazy import so project works without openai installed for non-AI paths
            from openai import OpenAI
            import httpx
            import certifi

            # Explicitly pass a default httpx client without proxies arg to avoid env injections
            http_client = httpx.Client(
                timeout=60.0,
                verify=certifi.where(),
                transport=httpx.HTTPTransport(retries=1),
                trust_env=False,  # ignore system proxy env that may inject unsupported args
            )
            client = OpenAI(
                api_key=self.api_key or os.environ.get("OPENAI_API_KEY", "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"),
                http_client=http_client,
                base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                max_retries=0,
            )
            resp = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=params.temperature,
                max_tokens=params.max_tokens,
                response_format={"type": "json_object"},
            )
            return resp.choices[0].message.content or ""
        except Exception as e:  # pragma: no cover - network
            # Include exception class for better diagnostics
            return f"ERROR: {e.__class__.__name__}: {e}"



