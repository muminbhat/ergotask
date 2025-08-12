from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from contexts.models import ContextEntry, ContextSourceType


@dataclass
class ContextCreateDTO:
    content: str
    source_type: str
    raw_metadata: dict | None = None
    owner_id: int | None = None


class ContextService:
    @staticmethod
    @transaction.atomic
    def ingest(dto: ContextCreateDTO) -> ContextEntry:
        entry = ContextEntry.objects.create(
            content=dto.content,
            source_type=dto.source_type,
            raw_metadata=dto.raw_metadata or {},
            owner_id=dto.owner_id,
        )
        return entry


