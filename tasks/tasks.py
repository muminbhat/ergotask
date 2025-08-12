from __future__ import annotations

from celery import shared_task

from .models import Task
from .services.task_service import TaskService
from ai.orchestrator import AiOrchestrator
from ai.provider_factory import get_provider


@shared_task
def recompute_priorities() -> int:
    count = 0
    for task in Task.objects.all():
        old = task.priority_score
        task.priority_score = TaskService.recompute_priority(task)
        if task.priority_score != old:
            task.save(update_fields=["priority_score"])
            count += 1
    return count


@shared_task
def ai_recompute_priorities(limit: int | None = None) -> int:
    """Use the AI orchestrator to refresh priority scores for tasks.

    Optionally limit the number of tasks processed (e.g., newest first by updated_at).
    """
    qs = Task.objects.select_related("category").prefetch_related("contexts").order_by("-updated_at")
    if limit:
        qs = qs[: int(limit)]
    orchestrator = AiOrchestrator(get_provider())
    updated = 0
    for task in qs:
        payload_task = {
            "title": task.title,
            "description": task.description,
            "category_name": task.category.name if task.category else None,
            "status": task.status,
            "due_date": task.due_date.isoformat() if task.due_date else None,
        }
        payload_contexts = [
            {"id": str(c.id), "source_type": c.source_type, "content": c.content}
            for c in task.contexts.all()[:10]
        ]
        bundle = orchestrator.suggest_for_task(task=payload_task, contexts=payload_contexts)
        try:
            pr = float(bundle.priority_score)
            pr = max(0.0, min(1.0, pr))
        except Exception:
            pr = task.priority_score
        if pr != task.priority_score:
            task.priority_score = pr
            task.save(update_fields=["priority_score"])
            updated += 1
    return updated


