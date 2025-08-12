from __future__ import annotations

import uuid
from django.db import models
from django.conf import settings


class ContextSourceType(models.TextChoices):
    WHATSAPP = "whatsapp", "WhatsApp"
    EMAIL = "email", "Email"
    NOTE = "note", "Note"
    OTHER = "other", "Other"


class ContextEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="contexts")
    content = models.TextField()
    source_type = models.CharField(max_length=20, choices=ContextSourceType.choices)
    raw_metadata = models.JSONField(default=dict, blank=True)
    processed_insights = models.JSONField(default=dict, blank=True)
    sentiment_score = models.FloatField(null=True, blank=True)
    keywords = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.source_type}: {self.content[:32]}"


