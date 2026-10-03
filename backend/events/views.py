import csv
import mimetypes
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.files.storage import default_storage
from django.db.models import Count, Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from .emails import send_login_alert, send_registration_confirmation, send_welcome_email
from .forms import EventForm, LoginForm, StudentProfileEditForm, StudentRegisterForm, UserEditForm
from .models import CATEGORY_ICONS, TEAM_SPORTS, Event, Registration, StudentProfile


def media_file(request, name):
    try:
        file = default_storage.open(name)
    except FileNotFoundError:
        raise Http404("File not found")
    content_type = getattr(file, "content_type", None) or mimetypes.guess_type(name)[0] or "application/octet-stream"
    response = HttpResponse(file.read(), content_type=content_type)
    response["Cache-Control"] = "public, max-age=86400"
    return response


def is_admin(user):
    return user.is_authenticated and user.is_staff


def admin_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not is_admin(request.user):
            messages.error(request, "Admin access is required for this page.")
            return redirect("login")
        return view_func(request, *args, **kwargs)

    return login_required(wrapper)


def student_required(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("login")
        if request.user.is_staff:
            messages.info(request, "Admins manage events from the admin dashboard.")
            return redirect("admin_dashboard")
        return view_func(request, *args, **kwargs)

    return wrapper


CATEGORY_TAGLINES = {
    "seminar": "Talks by experts & alumni",
    "workshop": "Hands-on skill building",
    "sports": "Compete for your department",
    "cultural": "Music, dance & drama",
    "technical": "Coding, quizzes & hackathons",
    "other": "Clubs, drives & more",
}


def home(request):
    open_events = Event.objects.filter(status__in=["upcoming", "ongoing"]).order_by("date", "time")
    events = list(open_events[:6])
    spotlights = [e for e in events if e.is_open]
    open_counts = {}
    for category in open_events.values_list("category", flat=True):
        open_counts[category] = open_counts.get(category, 0) + 1
    categories = [
        {
            "key": key,
            "label": label,
            "icon": CATEGORY_ICONS.get(key, "bi-stars"),
            "tagline": CATEGORY_TAGLINES.get(key, ""),
            "count": open_counts.get(key, 0),
        }
        for key, label in Event.CATEGORY_CHOICES
    ]
    completed = Event.objects.filter(status="completed")[:3]
    stats = {
        "events": Event.objects.count(),
        "open": sum(open_counts.values()),
        "students": StudentProfile.objects.count(),
        "registrations": Registration.objects.count(),
    }
    registered_ids = set()
    if spotlights and request.user.is_authenticated and not request.user.is_staff:
        registered_ids = set(
            Registration.objects.filter(student=request.user, event__in=spotlights).values_list("event_id", flat=True)
        )
    for event in spotlights:
        event.user_registered = event.pk in registered_ids
    return render(
        request,
        "events/home.html",
        {
            "events": events,
            "spotlights": spotlights,
            "categories": categories,
            "completed": completed,
            "stats": stats,
        },
    )


def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data["username"],
            password=form.cleaned_data["password"],
        )
        if user is not None:
            first_login = user.last_login is None
            login(request, user)
            name = user.get_full_name() or user.username
            if first_login:
                messages.success(request, f"Welcome, {name}!")
                send_login_alert(user, request)
            else:
                messages.success(request, f"Welcome back, {name}!")
            next_url = request.POST.get("next") or request.GET.get("next")
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                return redirect(next_url)
            return redirect("dashboard")
        messages.error(request, "Invalid username/email or password.")
    return render(request, "events/login.html", {"form": form, "next": request.GET.get("next", "")})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("home")


def student_register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = StudentRegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        profile = form.save()
        login(request, profile.user)
        # Keep last_login empty so the student's first real sign-in still gets the first-login email.
        User.objects.filter(pk=profile.user.pk).update(last_login=None)
        if send_welcome_email(profile.user):
            messages.success(
                request, f"Account created. A welcome email has been sent to {profile.user.email}."
            )
        else:
            messages.success(request, "Account created. You can now browse and register for events.")
        return redirect("student_dashboard")
    return render(request, "events/register.html", {"form": form})


@login_required
def dashboard(request):
    if is_admin(request.user):
        return redirect("admin_dashboard")
    return redirect("student_dashboard")


@admin_required
def admin_dashboard(request):
    events = Event.objects.annotate(reg_count=Count("registrations"))[:8]
    recent_regs = Registration.objects.select_related("student", "event")[:8]
    context = {
        "total_events": Event.objects.count(),
        "upcoming_events": Event.objects.filter(status="upcoming").count(),
        "total_students": StudentProfile.objects.count(),
        "total_registrations": Registration.objects.count(),
        "events": events,
        "recent_regs": recent_regs,
    }
    return render(request, "events/admin_dashboard.html", context)


@student_required
def student_dashboard(request):
    my_regs = Registration.objects.filter(student=request.user).select_related("event")
    registered_ids = my_regs.values_list("event_id", flat=True)
    upcoming = (
        Event.objects.filter(status__in=["upcoming", "ongoing"])
        .exclude(id__in=registered_ids)
        .order_by("date", "time")[:6]
    )
    return render(
        request,
        "events/student_dashboard.html",
        {
            "my_regs": my_regs,
            "upcoming": upcoming,
            "profile": getattr(request.user, "profile", None),
        },
    )


def event_list(request):
    events = Event.objects.all()
    category = request.GET.get("category", "")
    status = request.GET.get("status", "")
    q = request.GET.get("q", "")
    if category:
        events = events.filter(category=category)
    if status:
        events = events.filter(status=status)
    if q:
        events = events.filter(Q(title__icontains=q) | Q(venue__icontains=q) | Q(description__icontains=q))
    sections = [
        {
            "key": "active",
            "title": "Upcoming & ongoing events",
            "subtitle": "Open events you can still take part in",
            "events": events.filter(status__in=["upcoming", "ongoing"]).order_by("date", "time"),
        },
        {
            "key": "completed",
            "title": "Completed events",
            "subtitle": "Past events — registration is closed",
            "events": events.filter(status="completed"),
        },
        {
            "key": "cancelled",
            "title": "Cancelled events",
            "subtitle": "Events that will not take place",
            "events": events.filter(status="cancelled"),
        },
    ]
    return render(
        request,
        "events/event_list.html",
        {
            "events": events,
            "sections": [s for s in sections if s["events"]],
            "categories": Event.CATEGORY_CHOICES,
            "statuses": Event.STATUS_CHOICES,
            "selected_category": category,
            "selected_status": status,
            "q": q,
        },
    )


def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk)
    already = False
    if request.user.is_authenticated and not request.user.is_staff:
        already = Registration.objects.filter(student=request.user, event=event).exists()
    participants = []
    if is_admin(request.user):
        participants = event.registrations.select_related("student", "student__profile")
    return render(
        request,
        "events/event_detail.html",
        {"event": event, "already": already, "participants": participants},
    )


@admin_required
def event_create(request):
    form = EventForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        event = form.save(commit=False)
        event.created_by = request.user
        event.save()
        messages.success(request, f'Event "{event.title}" created successfully.')
        return redirect("event_detail", pk=event.pk)
    return render(
        request, "events/event_form.html", {"form": form, "title": "Create Event", "team_sports": TEAM_SPORTS}
    )


@admin_required
def event_edit(request, pk):
    event = get_object_or_404(Event, pk=pk)
    old_poster = event.poster.name
    form = EventForm(request.POST or None, request.FILES or None, instance=event)
    if request.method == "POST" and form.is_valid():
        form.save()
        if old_poster and old_poster != event.poster.name:
            default_storage.delete(old_poster)
        messages.success(request, "Event details updated.")
        return redirect("event_detail", pk=event.pk)
    return render(
        request,
        "events/event_form.html",
        {"form": form, "title": "Edit Event", "event": event, "team_sports": TEAM_SPORTS},
    )


@admin_required
def event_delete(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if request.method == "POST":
        title = event.title
        poster = event.poster.name
        event.delete()
        if poster:
            default_storage.delete(poster)
        messages.success(request, f'Event "{title}" has been deleted.')
        return redirect("event_list")
    return render(request, "events/event_confirm_delete.html", {"event": event})


@student_required
def register_event(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if request.method != "POST":
        return redirect("event_detail", pk=pk)
    if event.has_ended:
        messages.error(request, "This event has ended. Registration is closed.")
        return redirect("event_detail", pk=pk)
    if not event.is_open:
        messages.error(request, "This event is not open for registration.")
        return redirect("event_detail", pk=pk)
    if Registration.objects.filter(student=request.user, event=event).exists():
        messages.info(request, "You are already registered for this event.")
        return redirect("my_registrations")

    allowed = {"solo": ["solo"], "team": ["team"], "both": ["solo", "team"]}[event.participation_type]
    kind = request.POST.get("participation_type") or allowed[0]
    if kind not in allowed:
        messages.error(request, "Please choose a valid participation type.")
        return redirect("event_detail", pk=pk)

    team_name, members = "", []
    if kind == "team":
        team_name = request.POST.get("team_name", "").strip()[:100]
        members = [m.strip()[:100] for m in request.POST.getlist("member") if m.strip()]
        if not team_name:
            messages.error(request, "Please enter a team name.")
            return redirect("event_detail", pk=pk)
        if not members:
            messages.error(request, "Please add at least one other player to your team.")
            return redirect("event_detail", pk=pk)
        if len(members) + 1 > event.max_team_size:
            messages.error(request, f"A team can have at most {event.max_team_size} players.")
            return redirect("event_detail", pk=pk)

    registration = Registration.objects.create(
        student=request.user,
        event=event,
        participation_type=kind,
        team_name=team_name,
        team_members="\n".join(members),
    )
    if send_registration_confirmation(registration):
        messages.success(
            request, f'You are registered for "{event.title}". A confirmation email has been sent to {request.user.email}.'
        )
    else:
        messages.success(request, f'You are registered for "{event.title}".')
    return redirect("my_registrations")


@student_required
def cancel_registration(request, pk):
    registration = get_object_or_404(Registration, pk=pk, student=request.user)
    if registration.event.has_ended:
        messages.error(request, "This event has ended, so the registration can no longer be changed.")
        return redirect("my_registrations")
    if request.method == "POST":
        title = registration.event.title
        registration.delete()
        messages.success(request, f'Registration for "{title}" has been cancelled.')
    return redirect("my_registrations")


@student_required
def my_registrations(request):
    regs = Registration.objects.filter(student=request.user).select_related("event")
    return render(request, "events/my_registrations.html", {"regs": regs})


@admin_required
def participants(request, pk):
    event = get_object_or_404(Event, pk=pk)
    regs = event.registrations.select_related("student", "student__profile")
    return render(request, "events/participants.html", {"event": event, "regs": regs})


@admin_required
def participant_remove(request, pk):
    registration = get_object_or_404(Registration, pk=pk)
    event_id = registration.event_id
    if request.method == "POST":
        registration.delete()
        messages.success(request, "Participant removed.")
    return redirect("participants", pk=event_id)


REPORT_TIMELINE_DAYS = 90


def _report_payload():
    events = list(Event.objects.annotate(reg_count=Count("registrations")))
    registrations = list(Registration.objects.values_list("student_id", "registered_at", "participation_type"))
    departments = dict(StudentProfile.objects.values_list("user_id", "department"))
    category_labels = dict(Event.CATEGORY_CHOICES)
    status_labels = dict(Event.STATUS_CHOICES)
    department_labels = dict(StudentProfile.DEPARTMENT_CHOICES)

    by_category = {key: {"key": key, "label": label, "events": 0, "regs": 0} for key, label in Event.CATEGORY_CHOICES}
    by_status = {key: {"key": key, "label": label, "total": 0} for key, label in Event.STATUS_CHOICES}
    total_capacity = 0
    event_rows = []
    for e in events:
        by_category.setdefault(e.category, {"key": e.category, "label": e.category, "events": 0, "regs": 0})
        by_category[e.category]["events"] += 1
        by_category[e.category]["regs"] += e.reg_count
        by_status.setdefault(e.status, {"key": e.status, "label": e.status, "total": 0})
        by_status[e.status]["total"] += 1
        total_capacity += e.max_participants
        event_rows.append(
            {
                "id": str(e.pk),
                "title": e.title,
                "category": e.category,
                "category_label": category_labels.get(e.category, e.category),
                "date": e.date.isoformat(),
                "time": e.time.strftime("%H:%M") if e.time else "",
                "venue": e.venue,
                "status": e.status,
                "status_label": status_labels.get(e.status, e.status),
                "regs": e.reg_count,
                "capacity": e.max_participants,
                "fill": round(e.reg_count * 100 / e.max_participants, 1) if e.max_participants else 0,
                "detail_url": reverse("event_detail", args=[e.pk]),
                "participants_url": reverse("participants", args=[e.pk]),
                "export_url": reverse("export_participants", args=[e.pk]),
            }
        )

    def local_day(dt):
        return (timezone.localtime(dt) if timezone.is_aware(dt) else dt).date()

    today = timezone.localdate()
    reg_days = [local_day(r[1]) for r in registrations if r[1]]
    start = min([today - timedelta(days=REPORT_TIMELINE_DAYS - 1), *reg_days])
    per_day = {start + timedelta(days=i): 0 for i in range((today - start).days + 1)}
    for day in reg_days:
        if day in per_day:
            per_day[day] += 1
    by_department = {}
    by_type = {"solo": 0, "team": 0}
    for student_id, registered_at, participation_type in registrations:
        dept = departments.get(student_id, "Other")
        by_department[dept] = by_department.get(dept, 0) + 1
        by_type[participation_type] = by_type.get(participation_type, 0) + 1

    total_regs = len(registrations)
    return {
        "generated_at": timezone.localtime().isoformat(),
        "totals": {
            "events": len(events),
            "students": len(departments),
            "active_students": len({r[0] for r in registrations}),
            "registrations": total_regs,
            "capacity": total_capacity,
            "fill_rate": round(total_regs * 100 / total_capacity, 1) if total_capacity else 0,
            **{key: row["total"] for key, row in by_status.items()},
        },
        "by_category": [row for row in by_category.values() if row["events"]],
        "by_status": [row for row in by_status.values() if row["total"]],
        "by_department": sorted(
            ({"label": department_labels.get(k, k), "regs": v} for k, v in by_department.items()),
            key=lambda row: -row["regs"],
        ),
        "by_type": [{"key": k, "label": k.title(), "total": v} for k, v in by_type.items()],
        "timeline": [{"date": d.isoformat(), "count": c} for d, c in per_day.items()],
        "events": event_rows,
    }


@admin_required
def reports(request):
    return render(request, "events/reports.html", {"report": _report_payload()})


@admin_required
def reports_data(request):
    return JsonResponse(_report_payload())


@admin_required
def export_participants(request, pk):
    event = get_object_or_404(Event, pk=pk)
    regs = event.registrations.select_related("student", "student__profile")
    response = HttpResponse(content_type="text/csv")
    writer = csv.writer(response)
    writer.writerow(
        ["Roll Number", "Name", "Email", "Department", "Year", "Phone", "Type", "Team Name", "Team Players", "Registered At"]
    )
    for r in regs:
        profile = getattr(r.student, "profile", None)
        writer.writerow(
            [
                profile.roll_number if profile else "",
                r.student.get_full_name() or r.student.username,
                r.student.email,
                profile.department if profile else "",
                profile.get_year_display() if profile else "",
                profile.phone if profile else "",
                r.get_participation_type_display(),
                r.team_name,
                "; ".join(r.member_list),
                r.registered_at.strftime("%Y-%m-%d %H:%M"),
            ]
        )
    response["Content-Disposition"] = f'attachment; filename="{event.title[:40]}_participants.csv"'
    return response


ACTIVITY_LEVELS = {
    "today": {"label": "Active today", "badge": "badge-ongoing"},
    "week": {"label": "Active this week", "badge": "badge-upcoming"},
    "inactive": {"label": "Inactive", "badge": "badge-completed"},
    "never": {"label": "Never signed in", "badge": "badge-cancelled"},
}


def _activity(last_login, now):
    if last_login is None:
        return "never"
    if last_login >= now - timedelta(days=1):
        return "today"
    if last_login >= now - timedelta(days=7):
        return "week"
    return "inactive"


@admin_required
def user_monitoring(request, role):
    is_admin_view = role == "admins"
    users = User.objects.filter(is_staff=is_admin_view).order_by("-last_login", "-date_joined")
    if not is_admin_view:
        users = users.select_related("profile").annotate(reg_count=Count("event_registrations"))
    q = request.GET.get("q", "").strip()
    if q:
        users = users.filter(
            Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(email__icontains=q)
        )

    now = timezone.now()
    rows = []
    counts = {key: 0 for key in ACTIVITY_LEVELS}
    for u in users:
        level = _activity(u.last_login, now)
        counts[level] += 1
        rows.append({"user": u, "profile": getattr(u, "profile", None), "activity": {"key": level, **ACTIVITY_LEVELS[level]}})

    status = request.GET.get("status", "")
    if status in ACTIVITY_LEVELS:
        rows = [r for r in rows if r["activity"]["key"] == status]

    return render(
        request,
        "events/user_monitoring.html",
        {
            "role": role,
            "is_admin_view": is_admin_view,
            "rows": rows,
            "total": sum(counts.values()),
            "summary": [{"key": key, **info, "count": counts[key]} for key, info in ACTIVITY_LEVELS.items()],
            "status": status,
            "q": q,
        },
    )


def _monitor_url(user):
    return reverse("monitor_admins" if user.is_staff else "monitor_students")


def _managed_user(request, pk):
    """Fetch a user the current admin may change; superusers can only be changed by superusers."""
    target = get_object_or_404(User, pk=pk)
    if target.is_superuser and not request.user.is_superuser:
        messages.error(request, "Only a superuser can change another superuser's account.")
        return None
    return target


@admin_required
def user_edit(request, pk):
    target = _managed_user(request, pk)
    if target is None:
        return redirect("monitor_admins")
    profile = None if target.is_staff else getattr(target, "profile", None)
    form = UserEditForm(request.POST or None, instance=target)
    profile_form = StudentProfileEditForm(request.POST or None, instance=profile) if profile else None
    if request.method == "POST" and form.is_valid() and (profile_form is None or profile_form.is_valid()):
        form.save()
        if profile_form:
            profile_form.save()
        messages.success(request, f"Account for {target.get_full_name() or target.username} updated.")
        return redirect(_monitor_url(target))
    return render(
        request,
        "events/user_form.html",
        {"target": target, "form": form, "profile_form": profile_form, "back_url": _monitor_url(target)},
    )


@admin_required
def user_delete(request, pk):
    target = _managed_user(request, pk)
    if target is None:
        return redirect("monitor_admins")
    back_url = _monitor_url(target)
    if target.pk == request.user.pk:
        messages.error(request, "You cannot delete your own account.")
        return redirect(back_url)
    if request.method == "POST":
        name = target.get_full_name() or target.username
        Event.objects.filter(created_by=target).update(created_by=request.user)
        target.delete()
        messages.success(request, f"Account for {name} has been deleted.")
        return redirect(back_url)
    return render(
        request,
        "events/user_confirm_delete.html",
        {
            "target": target,
            "reg_count": Registration.objects.filter(student=target).count(),
            "event_count": Event.objects.filter(created_by=target).count(),
            "back_url": back_url,
        },
    )


@admin_required
def student_list(request):
    students = StudentProfile.objects.select_related("user").annotate(reg_count=Count("user__event_registrations"))
    q = request.GET.get("q", "")
    if q:
        students = students.filter(
            Q(roll_number__icontains=q)
            | Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
            | Q(user__username__icontains=q)
        )
    return render(request, "events/student_list.html", {"students": students, "q": q})
