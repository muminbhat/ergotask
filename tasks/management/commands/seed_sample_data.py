from __future__ import annotations

from django.core.management.base import BaseCommand
from django.utils import timezone

from catalog.models import Category
from contexts.models import ContextEntry, ContextSourceType
from tasks.models import Task, TaskStatus


class Command(BaseCommand):
    help = "Seed sample data: categories, contexts, tasks"

    def handle(self, *args, **options):
        # Categories
        categories = [
            "Work",
            "Personal",
            "Urgent",
            "Research",
        ]
        for name in categories:
            Category.objects.get_or_create(name=name)

        # Contexts
        ctx_samples = [
            (ContextSourceType.EMAIL, "Boss: please send the Q3 report by Wednesday."),
            (ContextSourceType.NOTE, "Buy groceries: milk, bread, eggs. Urgent for dinner today."),
            (ContextSourceType.WHATSAPP, "Client call moved to Friday 3pm. Prepare deck."),
        ]
        contexts = []
        for src, content in ctx_samples:
            ctx, _ = ContextEntry.objects.get_or_create(content=content, source_type=src)
            contexts.append(ctx)

        # Tasks
        work = Category.objects.get(name="Work")
        personal = Category.objects.get(name="Personal")

        t1, _ = Task.objects.get_or_create(
            title="Prepare Q3 report",
            defaults={
                "description": "Collect metrics and draft summary",
                "category": work,
                "status": TaskStatus.TODO,
                "due_date": timezone.now() + timezone.timedelta(days=2),
            },
        )
        t2, _ = Task.objects.get_or_create(
            title="Grocery shopping",
            defaults={
                "description": "Milk, bread, eggs",
                "category": personal,
                "status": TaskStatus.TODO,
                "due_date": timezone.now() + timezone.timedelta(days=1),
            },
        )
        if contexts:
            t1.contexts.add(contexts[0])
            t2.contexts.add(contexts[1])

        self.stdout.write(self.style.SUCCESS("Sample data seeded."))


