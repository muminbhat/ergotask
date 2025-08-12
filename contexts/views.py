from django_filters.rest_framework import DjangoFilterBackend
from django.db import models
from rest_framework import mixins, viewsets
from rest_framework.filters import OrderingFilter, SearchFilter

from .models import ContextEntry
from .serializers import ContextEntrySerializer
from .services.context_service import ContextCreateDTO, ContextService
from .tasks import process_context_entry


class ContextEntryViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = ContextEntry.objects.select_related("owner").all()
    serializer_class = ContextEntrySerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["source_type"]
    search_fields = ["content"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]

    def perform_create(self, serializer):
        validated = serializer.validated_data
        dto = ContextCreateDTO(
            content=validated["content"],
            source_type=validated["source_type"],
            raw_metadata=validated.get("raw_metadata", {}),
            owner_id=self.request.user.id if self.request and self.request.user and self.request.user.is_authenticated else None,
        )
        entry = ContextService.ingest(dto)
        serializer.instance = entry
        # Enqueue async processing unless running in eager mode
        process_context_entry.delay(str(entry.id))

    def get_queryset(self):
        qs = super().get_queryset()
        user = getattr(self.request, "user", None)
        if user and user.is_authenticated:
            return qs.filter(models.Q(owner=user) | models.Q(owner__isnull=True))
        return qs.none()


