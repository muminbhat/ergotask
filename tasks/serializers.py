from django.utils import timezone
from rest_framework import serializers

from catalog.serializers import CategorySerializer
from contexts.serializers import ContextEntrySerializer
from .models import Task


class TaskSerializer(serializers.ModelSerializer):
    category_detail = CategorySerializer(source="category", read_only=True)
    contexts_detail = ContextEntrySerializer(source="contexts", many=True, read_only=True)
    owner = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Task
        fields = [
            "id",
            "title",
            "description",
            "owner",
            "category",
            "category_detail",
            "status",
            "priority_score",
            "due_date",
            "ai_metadata",
            "contexts",
            "contexts_detail",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
            "priority_score",
            "category_detail",
            "contexts_detail",
        ]

    def validate_title(self, value: str) -> str:
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Title cannot be empty.")
        return value

    def validate_due_date(self, value):
        if value is None:
            return value
        # Allow slight past tolerance if needed later; for now strictly future or now
        now = timezone.now()
        if value.tzinfo is None:
            raise serializers.ValidationError("Due date must be timezone-aware (UTC recommended).")
        if value < now:
            raise serializers.ValidationError("Due date cannot be in the past.")
        return value


