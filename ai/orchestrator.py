from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional
import ast
import logging
import time
from datetime import timedelta, timezone as dt_timezone
from django.utils import timezone
import dateparser

from .providers.base import AiProvider, GenerateParams


@dataclass
class AiSuggestionBundle:
    priority_score: float
    suggested_deadline: Optional[str]
    enhanced_description: str
    categories: list[str]
    reasoning: str


SYSTEM_PROMPT = (
    "You are an assistant that analyzes tasks and daily context to produce:"
    " priority_score (0..1), suggested_deadline (ISO8601 or null), enhanced_description (string),"
    " categories (array of strings), reasoning (short string)."
    " Return ONLY a JSON object with exactly those keys. No extra keys or text."
    " The suggested_deadline must not be in the past relative to 'now' provided to you."
)


class AiOrchestrator:
    def __init__(self, provider: AiProvider):
        self.provider = provider

    def suggest_for_task(self, *, task: dict[str, Any], contexts: list[dict[str, Any]] | None = None) -> AiSuggestionBundle:
        now_iso = timezone.now().isoformat()
        payload = {
            "task": task,
            "contexts": contexts or [],
            "now": now_iso,
        }
        user_prompt = "Analyze and respond in JSON for this input (now is UTC '" + now_iso + "'):\n\n" + json.dumps(payload)

        t0 = time.time()
        raw = self.provider.generate(system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt, params=GenerateParams(max_tokens=500, temperature=0.2))
        dt_ms = int((time.time() - t0) * 1000)
        logger = logging.getLogger(__name__)
        logger.info(
            "ai.generate.completed",
            extra={
                "duration_ms": dt_ms,
                "task_title_len": len(task.get("title", "")),
                "contexts_count": len(contexts or []),
                "raw_prefix": (raw or "")[:200],
            },
        )
        if raw and raw.strip().startswith("ERROR:"):
            raise RuntimeError(raw.strip())

        try:
            # Try to locate a JSON object within the text if the model added prose
            data = self._parse_jsonlike(raw)
            # Normalize suggested_deadline to not be in the past
            suggested = data.get("suggested_deadline")
            normalized_deadline = None
            if isinstance(suggested, str) and suggested.strip():
                s = suggested.replace("Z", "+00:00")
                try:
                    dt = timezone.datetime.fromisoformat(s)
                    if timezone.is_naive(dt):
                        dt = timezone.make_aware(dt, timezone=timezone.utc)
                    now = timezone.now()
                    if dt < now:
                        dt = now + timedelta(days=1)
                    normalized_deadline = dt.astimezone(timezone.utc).isoformat()
                except Exception:
                    normalized_deadline = None

            return AiSuggestionBundle(
                priority_score=float(max(0.0, min(1.0, data.get("priority_score", 0.5)))),
                suggested_deadline=normalized_deadline,
                enhanced_description=data.get("enhanced_description", task.get("description", "")),
                categories=data.get("categories", []),
                reasoning=data.get("reasoning", ""),
            )
        except Exception as e:
            logger.exception("ai.generate.parse_error", extra={"raw_prefix": (raw or "")[:200]})
            # Fallback minimal bundle
            return AiSuggestionBundle(
                priority_score=0.5,
                suggested_deadline=task.get("due_date"),
                enhanced_description=task.get("description", ""),
                categories=[task.get("category_name")] if task.get("category_name") else [],
                reasoning=f"Fallback due to parse error: {e.__class__.__name__}",
            )

    @staticmethod
    def _parse_jsonlike(text: str) -> dict[str, Any]:
        if not text:
            raise ValueError("empty response")
        s = text.strip()
        # Remove markdown code fences
        if s.startswith("```"):
            # Strip first fence
            s = s.split("\n", 1)[1] if "\n" in s else s
            # If it starts with a language hint like json
            if s.lower().startswith("json\n"):
                s = s[5:]
            # Remove trailing fence
            if "```" in s:
                s = s.rsplit("```", 1)[0]
        # Extract the widest {...}
        start = s.find("{")
        end = s.rfind("}")
        candidate = s[start:end + 1] if start != -1 and end != -1 and end > start else s
        try:
            return json.loads(candidate)
        except Exception:
            # Attempt Python-literal parsing for single-quoted keys/strings
            obj = ast.literal_eval(candidate)
            if not isinstance(obj, dict):
                raise ValueError("response is not a JSON object")
            return obj


# --- Advanced AI helpers ---

@dataclass
class ContextAnalysis:
    keywords: list[str]
    sentiment_score: float
    has_urgency: bool
    entities: list[str]
    reasoning: str


@dataclass
class TimeBlock:
    start: str
    end: str
    label: str


@dataclass
class ScheduleSuggestion:
    blocks: list[TimeBlock]
    recommended_deadline: Optional[str]
    reasoning: str


CONTEXT_ANALYSIS_SYSTEM = (
    "You analyze a single context entry and respond ONLY JSON with keys: "
    "keywords (array of strings), sentiment_score (float -1..1), has_urgency (bool), "
    "entities (array of strings), reasoning (short string). No extra text."
)


SCHEDULE_SYSTEM = (
    "You propose a small schedule plan for the given task and context. Respond ONLY JSON with keys: "
    "blocks (array of objects with start, end (ISO8601 UTC), label), recommended_deadline (ISO8601 or null), reasoning (short). "
    "Keep blocks within the next 7 days and avoid past times relative to now."
)


class AiOrchestrator(AiOrchestrator):  # type: ignore[misc]
    def analyze_context(self, *, content: str, source_type: str) -> ContextAnalysis:
        payload = {"content": content, "source_type": source_type}
        user_prompt = "Analyze and respond in JSON for this context:\n\n" + json.dumps(payload)
        raw = self.provider.generate(
            system_prompt=CONTEXT_ANALYSIS_SYSTEM,
            user_prompt=user_prompt,
            params=GenerateParams(max_tokens=300, temperature=0.2),
        )
        data = self._parse_jsonlike(raw)
        return ContextAnalysis(
            keywords=list(data.get("keywords", [])),
            sentiment_score=float(max(-1.0, min(1.0, data.get("sentiment_score", 0.0)))),
            has_urgency=bool(data.get("has_urgency", False)),
            entities=list(data.get("entities", [])),
            reasoning=str(data.get("reasoning", "")),
        )

    def suggest_schedule(self, *, task: dict[str, Any], contexts: list[dict[str, Any]] | None = None) -> ScheduleSuggestion:
        now_iso = timezone.now().isoformat()
        payload = {"task": task, "contexts": contexts or [], "now": now_iso}
        user_prompt = "Suggest schedule and respond in JSON (now is UTC '" + now_iso + "'):\n\n" + json.dumps(payload)
        raw = self.provider.generate(
            system_prompt=SCHEDULE_SYSTEM,
            user_prompt=user_prompt,
            params=GenerateParams(max_tokens=600, temperature=0.2),
        )
        try:
            data = self._parse_jsonlike(raw)
            blocks = []
            for b in data.get("blocks", []) or []:
                start = str(b.get("start"))
                end = str(b.get("end"))
                label = str(b.get("label", "Work"))
                # best-effort sanitation
                if start and end:
                    blocks.append(TimeBlock(start=start, end=end, label=label))

            # normalize deadline to not be in past
            recommended = data.get("recommended_deadline")
            normalized_deadline = None
            if isinstance(recommended, str) and recommended.strip():
                s = recommended.replace("Z", "+00:00")
                try:
                    dt = timezone.datetime.fromisoformat(s)
                    if timezone.is_naive(dt):
                        dt = timezone.make_aware(dt, timezone=dt_timezone.utc)
                    if dt < timezone.now():
                        dt = timezone.now() + timedelta(days=1)
                    normalized_deadline = dt.astimezone(dt_timezone.utc).isoformat()
                except Exception:
                    normalized_deadline = None

            return ScheduleSuggestion(
                blocks=blocks,
                recommended_deadline=normalized_deadline,
                reasoning=str(data.get("reasoning", "")),
            )
        except Exception:
            # Fallback minimal one-block suggestion: tomorrow 09:00-11:00 UTC
            tomorrow = (timezone.now() + timedelta(days=1)).astimezone(dt_timezone.utc)
            start = tomorrow.replace(hour=9, minute=0, second=0, microsecond=0).isoformat()
            end = tomorrow.replace(hour=11, minute=0, second=0, microsecond=0).isoformat()
            return ScheduleSuggestion(
                blocks=[TimeBlock(start=start, end=end, label="Work on task")],
                recommended_deadline=None,
                reasoning="Fallback window suggested",
            )

    def select_context_ids(self, *, task: dict[str, Any], contexts: list[dict[str, Any]], k: int = 5) -> list[str]:
        """Ask the model to pick up to k most relevant context IDs for the task.

        Returns a list of context IDs (strings). Falls back to naive selection.
        """
        k = max(1, min(10, int(k or 5)))
        system = (
            "Select the most relevant contexts for the task. Respond ONLY JSON with key 'ids' as an array of up to K ids. "
            "No extra keys."
        )
        payload = {"task": task, "contexts": contexts, "k": k}
        raw = self.provider.generate(
            system_prompt=system,
            user_prompt="k=" + str(k) + "\n" + json.dumps(payload),
            params=GenerateParams(max_tokens=200, temperature=0.1),
        )
        try:
            data = self._parse_jsonlike(raw)
            ids = [str(x) for x in (data.get("ids") or [])][:k]
            if ids:
                return ids
        except Exception:
            pass
        # fallback: take first k
        return [str(c.get("id")) for c in contexts[:k] if c.get("id")]

    def generate_tasks_from_text(self, *, text: str) -> list[dict[str, Any]]:
        """Generate multiple tasks from free text.

        Returns list of { title, description, categories, due_date } where due_date is ISO8601 UTC string or null.
        """
        system = (
            "Extract actionable tasks and any explicit or implied future deadlines. "
            "Respond ONLY JSON with key 'tasks' as an array of objects with keys: "
            "title (string), description (string), categories (array of strings), due_date (ISO8601 UTC or null). "
            "Rules: (1) Interpret relative phrases like 'tomorrow' using the provided 'now' timestamp. "
            "(2) Never return a due_date in the past; if ambiguous, choose the soonest future date. "
            "(3) If only a date is known without time, set 09:00 UTC. Do not include extra keys or text."
        )
        now_iso = timezone.now().astimezone(dt_timezone.utc).isoformat()
        user_prompt = "now=" + now_iso + "\n" + text
        raw = self.provider.generate(
            system_prompt=system,
            user_prompt=user_prompt,
            params=GenerateParams(max_tokens=800, temperature=0.2),
        )
        data = self._parse_jsonlike(raw)
        tasks: list[dict[str, Any]] = []
        for t in data.get("tasks", []) or []:
            title = str(t.get("title", "")).strip()[:200]
            description = str(t.get("description", "")).strip()
            categories = [str(x) for x in (t.get("categories") or [])]
            due_raw = t.get("due_date") or None
            normalized_due: Optional[str] = None
            if isinstance(due_raw, str) and due_raw.strip():
                # Try strict ISO first; otherwise fall back to robust natural language parsing
                s = due_raw.replace("Z", "+00:00")
                dt = None
                try:
                    dt = timezone.datetime.fromisoformat(s)
                    if timezone.is_naive(dt):
                        dt = timezone.make_aware(dt, timezone=dt_timezone.utc)
                except Exception:
                    pass
                if dt is None:
                    parsed = dateparser.parse(due_raw, settings={
                        'RELATIVE_BASE': timezone.now().astimezone(dt_timezone.utc).replace(tzinfo=None),
                        'RETURN_AS_TIMEZONE_AWARE': False,
                        'PREFER_DATES_FROM': 'future',
                        'TIMEZONE': 'UTC',
                    })
                    if parsed:
                        dt = timezone.make_aware(parsed, timezone=dt_timezone.utc)
                if dt is not None:
                    now = timezone.now().astimezone(dt_timezone.utc)
                    if dt < now:
                        dt = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
                    normalized_due = dt.astimezone(dt_timezone.utc).isoformat()
            tasks.append({
                "title": title,
                "description": description,
                "categories": categories,
                "due_date": normalized_due,
            })
        return tasks


