from __future__ import annotations

from django.core.management.base import BaseCommand

from catalog.models import Category


DEFAULT_CATEGORIES = [
    "Work",
    "Personal",
    "Urgent",
    "Follow-up",
    "Research",
    "Finance",
    "Health",
    "Learning",
    "Shopping",
]


class Command(BaseCommand):
    help = "Seed default categories if they do not exist"

    def handle(self, *args, **options):
        created_count = 0
        for name in DEFAULT_CATEGORIES:
            _, created = Category.objects.get_or_create(name=name)
            if created:
                created_count += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded categories. Created: {created_count}, Total: {Category.objects.count()}"))


