from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class GenerateParams:
    temperature: float = 0.2
    max_tokens: int = 300


class AiProvider(Protocol):
    def generate(self, *, system_prompt: str, user_prompt: str, params: GenerateParams) -> str: ...


