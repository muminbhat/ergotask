from rest_framework import serializers

from .models import ContextEntry, ContextSourceType


class ContextEntrySerializer(serializers.ModelSerializer):
    owner = serializers.PrimaryKeyRelatedField(read_only=True)
    class Meta:
        model = ContextEntry
        fields = [
            "id",
            "owner",
            "content",
            "source_type",
            "raw_metadata",
            "processed_insights",
            "sentiment_score",
            "keywords",
            "created_at",
        ]
        read_only_fields = ["processed_insights", "sentiment_score", "keywords", "created_at"]

    def validate_content(self, value: str) -> str:
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Content cannot be empty.")
        if len(value) > 10000:
            raise serializers.ValidationError("Content too long (max 10000 characters).")
        return value

    def validate_source_type(self, value: str) -> str:
        if value not in ContextSourceType.values:
            raise serializers.ValidationError("Invalid source type.")
        return value


