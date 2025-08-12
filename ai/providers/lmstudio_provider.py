from __future__ import annotations

from dataclasses import dataclass
import requests

from .base import AiProvider, GenerateParams


@dataclass
class LmStudioProvider(AiProvider):
    base_url: str = "http://localhost:1234/v1"
    model: str = "qwen2.5:3b"

    def generate(self, *, system_prompt: str, user_prompt: str, params: GenerateParams) -> str:
        try:
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": params.temperature,
                    "max_tokens": params.max_tokens,
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:  # pragma: no cover
            return f"ERROR: {e}"


