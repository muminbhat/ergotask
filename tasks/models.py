from __future__ import annotations

import uuid
from django.db import models
from django.conf import settings

from catalog.models import Category
from contexts.models import ContextEntry


class TaskStatus(models.TextChoices):
    TODO = "todo", "To Do"
    IN_PROGRESS = "in_progress", "In Progress"
    DONE = "done", "Done"
    ARCHIVED = "archived", "Archived"


class Task(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=20, choices=TaskStatus.choices, default=TaskStatus.TODO)
    priority_score = models.FloatField(default=0.0)
    due_date = models.DateTimeField(null=True, blank=True)
    ai_metadata = models.JSONField(default=dict, blank=True)
    contexts = models.ManyToManyField(ContextEntry, blank=True, related_name="tasks")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-priority_score", "due_date", "-created_at"]
        indexes = [
            models.Index(fields=["priority_score"]),
            models.Index(fields=["due_date"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.title


