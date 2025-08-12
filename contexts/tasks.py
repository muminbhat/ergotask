from __future__ import annotations

import re
from collections import Counter
from typing import Iterable

from celery import shared_task
from django.db import transaction

from .models import ContextEntry
from ai.orchestrator import AiOrchestrator
from ai.provider_factory import get_provider


def _extract_keywords(text: str, max_keywords: int = 10) -> list[str]:
    words = re.findall(r"[A-Za-z]{4,}", text.lower())
    stop = {"this", "that", "with", "from", "have", "will", "your", "about", "https", "http"}
    filtered = [w for w in words if w not in stop]
    common = Counter(filtered).most_common(max_keywords)
    return [w for w, _ in common]


@shared_task
def process_context_entry(entry_id: str) -> None:
    entry = ContextEntry.objects.filter(id=entry_id).first()
    if not entry:
        return

    # Prefer AI analysis when available, fallback to heuristic
    content = entry.content or ""
    try:
        orchestrator = AiOrchestrator(get_provider())
        analysis = orchestrator.analyze_context(content=content, source_type=entry.source_type)
        keywords = list(analysis.keywords or []) or _extract_keywords(content)
        sentiment = float(analysis.sentiment_score)
        insights = {
            "length": len(content),
            "has_urgency": bool(analysis.has_urgency),
            "source_type": entry.source_type,
            "entities": analysis.entities,
            "keyword_count": len(keywords),
            "reasoning": analysis.reasoning,
        }
    except Exception:
        keywords = _extract_keywords(content)
        sentiment = 0.0
        urgent_cues = ["urgent", "asap", "immediately", "today", "deadline", "overdue"]
        positive_cues = ["thanks", "great", "good", "well done", "appreciate"]
        negative_cues = ["delay", "problem", "issue", "blocked", "fail"]
        for cue in urgent_cues:
            if cue in content.lower():
                sentiment += 0.2
        for cue in positive_cues:
            if cue in content.lower():
                sentiment += 0.1
        for cue in negative_cues:
            if cue in content.lower():
                sentiment -= 0.1
        insights = {
            "length": len(content),
            "has_urgency": any(c in content.lower() for c in urgent_cues),
            "source_type": entry.source_type,
            "keyword_count": len(keywords),
        }

    with transaction.atomic():
        entry.keywords = keywords
        entry.sentiment_score = max(-1.0, min(1.0, sentiment))
        entry.processed_insights = insights
        entry.save(update_fields=["keywords", "sentiment_score", "processed_insights"])


