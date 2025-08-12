from django.contrib import admin

from .models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "status",
        "priority_score",
        "due_date",
        "created_at",
    )
    search_fields = ("title", "description")
    list_filter = ("status", "category", "due_date", "created_at")
    ordering = ("-priority_score", "due_date", "-created_at")
    filter_horizontal = ("contexts",)


