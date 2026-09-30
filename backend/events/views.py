import csv

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import EventForm, LoginForm, StudentRegisterForm
from .models import TEAM_SPORTS, Event, Registration, StudentProfile


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


def home(request):
    events = Event.objects.filter(status__in=["upcoming", "ongoing"]).order_by("date", "time")[:6]
    completed = Event.objects.filter(status="completed")[:3]
    stats = {
        "events": Event.objects.count(),
        "students": StudentProfile.objects.count(),
        "registrations": Registration.objects.count(),
    }
    return render(request, "events/home.html", {"events": events, "completed": completed, "stats": stats})


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
            login(request, user)
            messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
            next_url = request.POST.get("next") or request.GET.get("next")
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                return redirect(next_url)
            return redirect("dashboard")
        messages.error(request, "Invalid username or password.")
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
    form = EventForm(request.POST or None, request.FILES or None, instance=event)
    if request.method == "POST" and form.is_valid():
        form.save()
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
        event.delete()
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

    Registration.objects.create(
        student=request.user,
        event=event,
        participation_type=kind,
        team_name=team_name,
        team_members="\n".join(members),
    )
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


@admin_required
def reports(request):
    events = Event.objects.annotate(reg_count=Count("registrations"))
    category_labels = dict(Event.CATEGORY_CHOICES)
    status_labels = dict(Event.STATUS_CHOICES)
    by_category = [
        {
            "key": row["category"],
            "label": category_labels.get(row["category"], row["category"]),
            "total": row["total"],
            "regs": row["regs"],
        }
        for row in (
            Event.objects.values("category")
            .annotate(total=Count("id"), regs=Count("registrations"))
            .order_by("-total")
        )
    ]
    by_status = [
        {
            "key": row["status"],
            "label": status_labels.get(row["status"], row["status"]),
            "total": row["total"],
        }
        for row in Event.objects.values("status").annotate(total=Count("id")).order_by("-total")
    ]
    top_events = events.order_by("-reg_count")[:5]
    context = {
        "total_events": Event.objects.count(),
        "total_students": StudentProfile.objects.count(),
        "total_registrations": Registration.objects.count(),
        "upcoming": Event.objects.filter(status="upcoming").count(),
        "completed": Event.objects.filter(status="completed").count(),
        "by_category": by_category,
        "by_status": by_status,
        "top_events": top_events,
        "events": events,
    }
    return render(request, "events/reports.html", context)


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
