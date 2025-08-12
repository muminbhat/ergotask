from django.contrib import admin

from .models import ContextEntry


@admin.register(ContextEntry)
class ContextEntryAdmin(admin.ModelAdmin):
    list_display = ("source_type", "created_at", "sentiment_score")
    search_fields = ("content",)
    list_filter = ("source_type", "created_at")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)


