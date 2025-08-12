from django.contrib import admin

from .models import Category


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "usage_count", "last_used_at")
    search_fields = ("name",)
    list_filter = ("last_used_at",)
    ordering = ("name",)


