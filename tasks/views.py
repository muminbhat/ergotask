from django_filters.rest_framework import DjangoFilterBackend
from django.db import models
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter, SearchFilter
from rest_framework.response import Response

from .models import Task
from .serializers import TaskSerializer
from .services.task_service import TaskCreateDTO, TaskService, TaskUpdateDTO
from ai.orchestrator import AiOrchestrator
from ai.provider_factory import get_provider
from catalog.models import Category
from catalog.services.category_service import CategoryService
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from django.http import HttpResponse
import csv
import io
import json
from django.utils import timezone as tz


class TaskViewSet(
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Task.objects.select_related("category", "owner").prefetch_related("contexts")
    serializer_class = TaskSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["category", "status"]
    search_fields = ["title", "description"]
    ordering_fields = ["priority_score", "due_date", "created_at"]
    ordering = ["-priority_score", "due_date", "-created_at"]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    @action(detail=True, methods=["post"], url_path="ai-suggestions")
    def ai_suggestions(self, request, pk=None):
        task = self.get_object()

        orchestrator = AiOrchestrator(get_provider())
        payload_task = {
            "title": task.title,
            "description": task.description,
            "category_name": task.category.name if task.category else None,
            "status": task.status,
            "due_date": task.due_date.isoformat() if task.due_date else None,
        }
        payload_contexts = [
            {"id": str(c.id), "source_type": c.source_type, "content": c.content}
            for c in task.contexts.all()[:10]
        ]
        bundle = orchestrator.suggest_for_task(task=payload_task, contexts=payload_contexts)

        return Response(
            {
                "priority_score": bundle.priority_score,
                "suggested_deadline": bundle.suggested_deadline,
                "enhanced_description": bundle.enhanced_description,
                "categories": bundle.categories,
                "reasoning": bundle.reasoning,
            }
        )

    @action(detail=False, methods=["post"], url_path="ai-bulk-suggestions")
    def ai_bulk_suggestions(self, request):
        ids = request.data if isinstance(request.data, list) else request.data.get("task_ids", [])
        if not isinstance(ids, list) or not ids:
            return Response({"detail": "Provide task_ids as a non-empty array"}, status=400)
        tasks = list(Task.objects.filter(id__in=ids).select_related("category").prefetch_related("contexts"))
        orchestrator = AiOrchestrator(get_provider())
        results = {}
        for t in tasks:
            payload_task = {
                "title": t.title,
                "description": t.description,
                "category_name": t.category.name if t.category else None,
                "status": t.status,
                "due_date": t.due_date.isoformat() if t.due_date else None,
            }
            payload_contexts = [
                {"id": str(c.id), "source_type": c.source_type, "content": c.content}
                for c in t.contexts.all()[:10]
            ]
            bundle = orchestrator.suggest_for_task(task=payload_task, contexts=payload_contexts)
            results[str(t.id)] = {
                "priority_score": bundle.priority_score,
                "suggested_deadline": bundle.suggested_deadline,
                "enhanced_description": bundle.enhanced_description,
                "categories": bundle.categories,
                "reasoning": bundle.reasoning,
            }
        return Response(results)

    @action(detail=True, methods=["post"], url_path="ai-apply")
    def ai_apply(self, request, pk=None):
        """Run AI suggestions and persist best-effort updates on the server.

        Applies:
        - enhanced_description
        - suggested_deadline
        - category (match existing by case-insensitive name, otherwise auto-create from first suggestion)
        - priority_score
        Stores the raw suggestion in ai_metadata under key 'last_ai_apply'.
        """
        task = self.get_object()

        orchestrator = AiOrchestrator(get_provider())
        payload_task = {
            "title": task.title,
            "description": task.description,
            "category_name": task.category.name if task.category else None,
            "status": task.status,
            "due_date": task.due_date.isoformat() if task.due_date else None,
        }
        payload_contexts = [
            {"id": str(c.id), "source_type": c.source_type, "content": c.content}
            for c in task.contexts.all()[:10]
        ]
        bundle = orchestrator.suggest_for_task(task=payload_task, contexts=payload_contexts)

        # Apply description
        if bundle.enhanced_description:
            task.description = bundle.enhanced_description

        # Apply deadline
        if bundle.suggested_deadline:
            try:
                s = bundle.suggested_deadline.replace("Z", "+00:00")
                dt = timezone.datetime.fromisoformat(s)
                if timezone.is_naive(dt):
                    dt = timezone.make_aware(dt, timezone=timezone.utc)
                task.due_date = dt
            except Exception:
                # ignore parse errors; keep existing due_date
                pass

        # Apply category via best effort matching
        chosen_category = None
        suggestions = bundle.categories or []
        # Exact (case-insensitive) match first
        for name in suggestions:
            existing = Category.objects.filter(name__iexact=str(name).strip()).first()
            if existing:
                chosen_category = existing
                break
        # If still none and we have at least one suggestion, create the first
        if not chosen_category and suggestions:
            first_name = str(suggestions[0]).strip()
            if first_name:
                chosen_category, _ = Category.objects.get_or_create(name=first_name)
        if chosen_category:
            task.category = chosen_category

        # Apply priority score
        try:
            pr = float(bundle.priority_score)
            task.priority_score = max(0.0, min(1.0, pr))
        except Exception:
            pass

        # Record metadata
        meta = dict(task.ai_metadata or {})
        meta["last_ai_apply"] = {
            "priority_score": bundle.priority_score,
            "suggested_deadline": bundle.suggested_deadline,
            "categories": suggestions,
            "reasoning": bundle.reasoning,
        }
        task.ai_metadata = meta

        task.save()

        # Touch category usage if applicable
        if chosen_category:
            try:
                CategoryService.touch_usage(chosen_category)
            except Exception:
                pass

        serializer = self.get_serializer(task)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="schedule-suggestions")
    def schedule_suggestions(self, request, pk=None):
        task = self.get_object()
        orchestrator = AiOrchestrator(get_provider())
        payload_task = {
            "title": task.title,
            "description": task.description,
            "category_name": task.category.name if task.category else None,
            "status": task.status,
            "due_date": task.due_date.isoformat() if task.due_date else None,
        }
        payload_contexts = [
            {"id": str(c.id), "source_type": c.source_type, "content": c.content}
            for c in task.contexts.all()[:10]
        ]
        suggestion = orchestrator.suggest_schedule(task=payload_task, contexts=payload_contexts)
        return Response(
            {
                "blocks": [
                    {"start": b.start, "end": b.end, "label": b.label}
                    for b in suggestion.blocks
                ],
                "recommended_deadline": suggestion.recommended_deadline,
                "reasoning": suggestion.reasoning,
            }
        )

    @action(detail=False, methods=["post"], url_path="nl-create")
    def nl_create(self, request):
        """Create multiple tasks from free-text input via AI."""
        text = (request.data.get("text") or "").strip()
        if not text:
            return Response({"detail": "Provide 'text'"}, status=400)
        orchestrator = AiOrchestrator(get_provider())
        tasks = orchestrator.generate_tasks_from_text(text=text)
        created = []
        for t in tasks:
            cat = None
            # try exact match for first category
            cats = t.get("categories") or []
            for name in cats:
                existing = Category.objects.filter(name__iexact=str(name).strip()).first()
                if existing:
                    cat = existing
                    break
            if not cat and cats:
                cat, _ = Category.objects.get_or_create(name=str(cats[0]).strip()[:100])
            # parse due_date if provided
            due_val = None
            due_iso = t.get("due_date")
            if due_iso:
                try:
                    s = str(due_iso).replace("Z", "+00:00")
                    dt = timezone.datetime.fromisoformat(s)
                    if timezone.is_naive(dt):
                        dt = timezone.make_aware(dt, timezone=timezone.utc)
                    due_val = dt
                except Exception:
                    due_val = None
            dto = TaskCreateDTO(title=t.get("title") or "Untitled", description=t.get("description") or "", category=cat, due_date=due_val)
            task = TaskService.create_task(dto)
            if cat:
                try:
                    CategoryService.touch_usage(cat)
                except Exception:
                    pass
            created.append(str(task.id))
        return Response({"created": created, "count": len(created)})

    @action(detail=True, methods=["post"], url_path="link-contexts-ai")
    def link_contexts_ai(self, request, pk=None):
        """Link top-k contexts to task using AI selection (no embeddings dependency)."""
        task = self.get_object()
        k = int(request.data.get("k") or 5)
        payload_task = {
            "title": task.title,
            "description": task.description,
            "category_name": task.category.name if task.category else None,
            "status": task.status,
            "due_date": task.due_date.isoformat() if task.due_date else None,
        }
        all_contexts = [
            {"id": str(c.id), "source_type": c.source_type, "content": c.content}
            for c in task.contexts.all()[:10]
        ]
        # If task has no contexts yet, consider recent global contexts
        if not all_contexts:
            from contexts.models import ContextEntry

            recent = list(ContextEntry.objects.order_by("-created_at")[:50])
            all_contexts = [
                {"id": str(c.id), "source_type": c.source_type, "content": c.content}
                for c in recent
            ]

        orchestrator = AiOrchestrator(get_provider())
        ids = orchestrator.select_context_ids(task=payload_task, contexts=all_contexts, k=k)
        from contexts.models import ContextEntry

        selected = list(ContextEntry.objects.filter(id__in=ids))
        if selected:
            task.contexts.add(*selected)
        return Response({"linked": [str(c.id) for c in selected]})

    @action(detail=False, methods=["post"], url_path="auto-plan-day")
    def auto_plan_day(self, request):
        """Suggest a daily plan across active tasks (todo/in_progress)."""
        tasks = list(
            Task.objects.filter(status__in=["todo", "in_progress"]).select_related("category").prefetch_related("contexts")
        )
        orchestrator = AiOrchestrator(get_provider())
        now_iso = tz.now().isoformat()
        plan = []
        for t in tasks[:10]:
            payload_task = {
                "title": t.title,
                "description": t.description,
                "category_name": t.category.name if t.category else None,
                "status": t.status,
                "due_date": t.due_date.isoformat() if t.due_date else None,
            }
            payload_contexts = [
                {"id": str(c.id), "source_type": c.source_type, "content": c.content}
                for c in t.contexts.all()[:5]
            ]
            s = orchestrator.suggest_schedule(task=payload_task, contexts=payload_contexts)
            plan.append(
                {
                    "task_id": str(t.id),
                    "title": t.title,
                    "blocks": [{"start": b.start, "end": b.end, "label": b.label} for b in s.blocks],
                    "recommended_deadline": s.recommended_deadline,
                    "reasoning": s.reasoning,
                }
            )
        return Response({"now": now_iso, "plan": plan})

    @action(detail=False, methods=["post"], url_path="seed-sample-data")
    def seed_sample_data(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=401)
        # Ensure base categories
        for name in ["Work", "Personal", "Health", "Finance"]:
            Category.objects.get_or_create(name=name)
        # Seed contexts
        from contexts.models import ContextEntry
        ctxs = ContextEntry.objects.filter(owner=user)
        if ctxs.count() < 6:
            defaults = [
                ("whatsapp", "Client moved meeting to Friday 10am"),
                ("email", "Boss: please send Q3 projections by next Tuesday"),
                ("note", "Buy groceries: milk, bread, eggs"),
                ("note", "Gym schedule: 3x this week"),
                ("email", "Invoice payment reminder due in 5 days"),
                ("whatsapp", "Trip planning with friends next month"),
            ]
            need = 6 - ctxs.count()
            for stype, content in defaults[:need]:
                ContextEntry.objects.create(owner=user, source_type=stype, content=content, raw_metadata={})
        # Seed tasks
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
        statuses = ["todo", "in_progress", "done", "archived"]
        count = Task.objects.filter(owner=user).count()
        for i in range(count, 10):
            Task.objects.create(
                owner=user,
                title=titles[i % len(titles)],
                description="Seeded task",
                category=Category.objects.order_by('?').first(),
                status=statuses[i % len(statuses)],
                due_date=tz.now() + tz.timedelta(days=i),
                priority_score=min(0.95, 0.2 + (i * 0.05)),
            )
        return Response({"ok": True})

    @action(detail=False, methods=["get"], url_path="export")
    def export(self, request):
        fmt = (request.query_params.get("format") or "json").lower()
        qs = self.filter_queryset(self.get_queryset())
        qs = qs.order_by("-created_at")

        if fmt == "csv":
            buffer = io.StringIO()
            writer = csv.writer(buffer)
            writer.writerow(["id", "title", "description", "category", "status", "priority_score", "due_date"])
            for t in qs:
                writer.writerow([
                    str(t.id),
                    t.title,
                    t.description,
                    t.category.name if t.category else "",
                    t.status,
                    f"{t.priority_score:.2f}",
                    t.due_date.isoformat() if t.due_date else "",
                ])
            resp = HttpResponse(buffer.getvalue(), content_type="text/csv")
            resp["Content-Disposition"] = 'attachment; filename="tasks_export.csv"'
            return resp

        # default json
        data = []
        for t in qs:
            data.append({
                "id": str(t.id),
                "title": t.title,
                "description": t.description,
                "category": t.category.name if t.category else None,
                "status": t.status,
                "priority_score": t.priority_score,
                "due_date": t.due_date.isoformat() if t.due_date else None,
            })
        resp = HttpResponse(json.dumps(data), content_type="application/json")
        resp["Content-Disposition"] = 'attachment; filename="tasks_export.json"'
        return resp

    @action(detail=False, methods=["post"], url_path="import")
    def import_(self, request):
        """Import tasks from uploaded file (CSV/JSON) or JSON body.

        CSV columns: title, description, category, status, due_date (ISO8601)
        JSON: array of objects with same keys.
        """
        created_ids: list[str] = []

        def upsert_category(name: str | None) -> Category | None:
            if not name:
                return None
            name = str(name).strip()
            if not name:
                return None
            obj, _ = Category.objects.get_or_create(name=name)
            return obj

        uploaded = request.FILES.get("file")
        items = None
        if uploaded:
            content = uploaded.read()
            name = (uploaded.name or "").lower()
            if name.endswith(".csv"):
                text = content.decode("utf-8", errors="ignore")
                reader = csv.DictReader(io.StringIO(text))
                items = list(reader)
            else:
                items = json.loads(content.decode("utf-8", errors="ignore"))
        else:
            # Try JSON body
            try:
                items = request.data
                if isinstance(items, dict) and "items" in items:
                    items = items["items"]
            except Exception:
                items = None

        if not isinstance(items, list) or not items:
            return Response({"detail": "Provide a CSV/JSON file or JSON array in body."}, status=400)

        for obj in items:
            try:
                title = (obj.get("title") or obj.get("Title") or "").strip()
                if not title:
                    continue
                description = obj.get("description") or obj.get("Description") or ""
                category_name = obj.get("category") or obj.get("Category")
                status_val = obj.get("status") or obj.get("Status") or Task._meta.get_field("status").default
                due_iso = obj.get("due_date") or obj.get("DueDate") or None
                due_val = None
                if due_iso:
                    try:
                        s = str(due_iso).replace("Z", "+00:00")
                        dt = timezone.datetime.fromisoformat(s)
                        if timezone.is_naive(dt):
                            dt = timezone.make_aware(dt, timezone=timezone.utc)
                        due_val = dt
                    except Exception:
                        due_val = None
                category_obj = upsert_category(category_name)
                dto = TaskCreateDTO(
                    title=title,
                    description=description,
                    category=category_obj,
                    status=status_val,
                    due_date=due_val,
                    contexts_ids=None,
                )
                task = TaskService.create_task(dto)
                if category_obj:
                    try:
                        CategoryService.touch_usage(category_obj)
                    except Exception:
                        pass
                created_ids.append(str(task.id))
            except Exception:
                continue

        return Response({"created": created_ids, "count": len(created_ids)})

    def perform_create(self, serializer):
        validated = serializer.validated_data
        dto = TaskCreateDTO(
            title=validated["title"],
            description=validated.get("description", ""),
            category=validated.get("category"),
            status=validated.get("status", Task._meta.get_field("status").default),
            due_date=validated.get("due_date"),
            contexts_ids=[c.id for c in validated.get("contexts", [])],
            owner_id=self.request.user.id if self.request and self.request.user and self.request.user.is_authenticated else None,
        )
        task = TaskService.create_task(dto)
        # refresh serializer instance
        serializer.instance = task

    def perform_update(self, serializer):
        validated = serializer.validated_data
        dto = TaskUpdateDTO(
            title=validated.get("title"),
            description=validated.get("description"),
            category=validated.get("category") if "category" in validated else None,
            status=validated.get("status"),
            due_date=validated.get("due_date") if "due_date" in validated else None,
            contexts_ids=[str(c.id) for c in validated.get("contexts", [])] if "contexts" in validated else None,
        )
        task = TaskService.update_task(serializer.instance, dto)
        serializer.instance = task

    def get_queryset(self):
        qs = super().get_queryset()
        user = getattr(self.request, "user", None)
        if user and user.is_authenticated:
            return qs.filter(models.Q(owner=user) | models.Q(owner__isnull=True))
        return qs.none()


