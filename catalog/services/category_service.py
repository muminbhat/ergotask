from __future__ import annotations

from catalog.models import Category


class CategoryService:
    @staticmethod
    def suggest_existing(names: list[str]) -> list[Category]:
        return list(Category.objects.filter(name__in=names))

    @staticmethod
    def touch_usage(category: Category) -> None:
        from django.utils import timezone

        category.usage_count = (category.usage_count or 0) + 1
        category.last_used_at = timezone.now()
        category.save(update_fields=["usage_count", "last_used_at"])


