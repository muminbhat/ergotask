from __future__ import annotations

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from uuid import uuid4

from catalog.models import Category
from contexts.models import ContextEntry, ContextSourceType
from tasks.models import Task, TaskStatus


class Command(BaseCommand):
    help = "Seed sample contexts and tasks for the current authenticated user id provided via --username"

    def add_arguments(self, parser):
        parser.add_argument("--username", type=str, required=True)

    def handle(self, *args, **options):
        User = get_user_model()
        username = options["username"]
        user = User.objects.filter(username=username).first()
        if not user:
            self.stderr.write(self.style.ERROR(f"User '{username}' not found"))
            return

        # Categories
        cat_names = ["Work", "Personal", "Health", "Finance"]
        categories = {name: Category.objects.get_or_create(name=name)[0] for name in cat_names}

        # Contexts (6)
        contexts_data = [
            ("whatsapp", "Client moved meeting to Friday 10am"),
            ("email", "Boss: please send Q3 projections by next Tuesday"),
            ("note", "Buy groceries: milk, bread, eggs"),
            ("note", "Gym schedule: 3x this week"),
            ("email", "Invoice payment reminder due in 5 days"),
            ("whatsapp", "Trip planning with friends next month"),
        ]
        contexts = []
        for stype, content in contexts_data:
            c = ContextEntry.objects.create(
                owner=user,
                source_type=stype,
                content=content,
                raw_metadata={},
            )
            contexts.append(c)

        # Tasks (10)
        import random
        now = timezone.now()
        statuses = [TaskStatus.TODO, TaskStatus.IN_PROGRESS, TaskStatus.DONE, TaskStatus.ARCHIVED]
        titles = [
            "Prepare Q3 report",
            "Email Pattabi about new servers",
            "Buy groceries",
            "Gym session",
            "Pay utility bill",
            "Code review backlog",
            "Plan team retro",
            "Refactor API endpoints",
            "Write test cases",
            "Archive old documents",
        ]
        for i, title in enumerate(titles):
            Task.objects.create(
                owner=user,
                title=title,
                description="Seeded task",
                category=random.choice(list(categories.values())),
                status=random.choice(statuses),
                due_date=(now + timezone.timedelta(days=random.randint(0, 14))),
                priority_score=random.random(),
            )

        self.stdout.write(self.style.SUCCESS(f"Seeded sample data for user '{username}'"))


