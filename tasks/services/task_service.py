from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

from django.db import transaction

from catalog.models import Category
from contexts.models import ContextEntry
from tasks.models import Task
from catalog.services.category_service import CategoryService


@dataclass
class TaskCreateDTO:
    title: str
    description: str = ""
    category: Optional[Category] = None
    status: str = Task._meta.get_field("status").default
    due_date: Optional[object] = None  # datetime, but keep loose typing for serializer compatibility
    contexts_ids: Optional[Iterable[str]] = None
    owner_id: Optional[int] = None


@dataclass
class TaskUpdateDTO:
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[Category] = None
    status: Optional[str] = None
    due_date: Optional[object] = None
    contexts_ids: Optional[Iterable[str]] = None


class TaskService:
    """Encapsulates task creation/update logic and priority computation."""

    @staticmethod
    @transaction.atomic
    def create_task(dto: TaskCreateDTO) -> Task:
        task = Task(
            title=dto.title,
            description=dto.description,
            category=dto.category,
            status=dto.status,
            due_date=dto.due_date,
            owner_id=dto.owner_id,
        )
        task.priority_score = TaskService._initial_priority(task)
        task.save()

        if dto.contexts_ids:
            contexts = list(ContextEntry.objects.filter(id__in=dto.contexts_ids))
            if contexts:
                task.contexts.add(*contexts)

        return task

    @staticmethod
    @transaction.atomic
    def update_task(task: Task, dto: TaskUpdateDTO) -> Task:
        if dto.title is not None:
            task.title = dto.title
        if dto.description is not None:
            task.description = dto.description
        if dto.category is not None or dto.category is None:
            # allow clearing category
            task.category = dto.category
        if dto.status is not None:
            task.status = dto.status
        if dto.due_date is not None or dto.due_date is None:
            # allow clearing due_date
            task.due_date = dto.due_date

        task.priority_score = TaskService.recompute_priority(task)
        task.save()

        if dto.contexts_ids is not None:
            contexts = list(ContextEntry.objects.filter(id__in=dto.contexts_ids))
            task.contexts.set(contexts)

        if task.category:
            try:
                CategoryService.touch_usage(task.category)
            except Exception:
                pass

        return task

    @staticmethod
    def recompute_priority(task: Task) -> float:
        """Hybrid scoring combining due-urgency + stored AI score + status boost."""
        from django.utils import timezone

        base = 0.2
        # due urgency within a week
        due_component = 0.0
        try:
            if task.due_date:
                delta_hours = max((task.due_date - timezone.now()).total_seconds() / 3600.0, 0.0)
                due_component = max(0.0, 1.0 - min(delta_hours / 168.0, 1.0))
        except Exception:
            pass

        # ai score if present in ai_metadata
        ai_component = 0.0
        try:
            meta = task.ai_metadata or {}
            ai_last = meta.get("last_ai_apply") or meta.get("last_ai") or {}
            ai_component = float(ai_last.get("priority_score", task.priority_score or 0.0))
        except Exception:
            ai_component = float(task.priority_score or 0.0)

        # status boost: in_progress gets a nudge
        status_boost = 0.1 if getattr(task, "status", "") == "in_progress" else 0.0

        final_score = 0.4 * ai_component + 0.3 * due_component + 0.2 * (task.priority_score or 0.0) + 0.1 * status_boost
        return float(max(0.0, min(1.0, final_score)))

    @staticmethod
    def _initial_priority(task: Task) -> float:
        return TaskService.recompute_priority(task)


