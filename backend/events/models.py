import re
from datetime import datetime, time

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

TEAM_SPORTS = {
    "cricket": 11,
    "football": 11,
    "soccer": 11,
    "hockey": 11,
    "volleyball": 6,
    "basketball": 5,
    "kabaddi": 7,
    "kho-kho": 9,
    "kho kho": 9,
    "throwball": 7,
    "handball": 7,
    "tug of war": 8,
    "relay": 4,
}

CATEGORY_ICONS = {
    "seminar": "bi-mic",
    "workshop": "bi-tools",
    "sports": "bi-trophy",
    "cultural": "bi-music-note-beamed",
    "technical": "bi-cpu",
}


def team_sport_size(title):
    """Return the standard squad size if the title names a team sport, else None."""
    lowered = (title or "").lower()
    for sport, size in TEAM_SPORTS.items():
        if re.search(rf"\b{re.escape(sport)}\b", lowered):
            return size
    return None


class StudentProfile(models.Model):
    YEAR_CHOICES = [
        ("1", "First Year"),
        ("2", "Second Year"),
        ("3", "Third Year"),
    ]
    DEPARTMENT_CHOICES = [
        ("BCA", "BCA"),
        ("BBA", "BBA"),
        ("BCom", "B.Com"),
        ("BSc", "B.Sc"),
        ("BA", "B.A"),
        ("MCA", "MCA"),
        ("MBA", "MBA"),
        ("Other", "Other"),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    roll_number = models.CharField(max_length=20, unique=True)
    department = models.CharField(max_length=20, choices=DEPARTMENT_CHOICES)
    year = models.CharField(max_length=2, choices=YEAR_CHOICES)
    phone = models.CharField(max_length=15)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.roll_number})"


class Event(models.Model):
    CATEGORY_CHOICES = [
        ("seminar", "Seminar"),
        ("workshop", "Workshop"),
        ("sports", "Sports Event"),
        ("cultural", "Cultural Event"),
        ("technical", "Technical Event"),
        ("other", "Other"),
    ]
    STATUS_CHOICES = [
        ("upcoming", "Upcoming"),
        ("ongoing", "Ongoing"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]
    PARTICIPATION_CHOICES = [
        ("solo", "Solo only"),
        ("team", "Team only"),
        ("both", "Solo or Team"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    date = models.DateField()
    time = models.TimeField()
    end_date = models.DateField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)
    venue = models.CharField(max_length=200)
    max_participants = models.PositiveIntegerField(default=50)
    participation_type = models.CharField(max_length=10, choices=PARTICIPATION_CHOICES, default="solo")
    max_team_size = models.PositiveSmallIntegerField(default=4)
    rules = models.TextField(blank=True, help_text="One rule per line.")
    student_coordinator_name = models.CharField(max_length=100, blank=True)
    student_coordinator_phone = models.CharField(max_length=15, blank=True)
    teacher_coordinator_name = models.CharField(max_length=100, blank=True)
    teacher_coordinator_phone = models.CharField(max_length=15, blank=True)
    poster = models.ImageField(upload_to="event_posters/", blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="upcoming")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="created_events")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-time"]

    def __str__(self):
        return self.title

    @classmethod
    def refresh_statuses(cls):
        """Move upcoming events to ongoing once they start, and to completed once they end."""
        now = timezone.now()
        candidates = cls.objects.filter(status__in=["upcoming", "ongoing"], date__lte=timezone.localdate())
        for event in candidates:
            if event.ends_at <= now:
                new_status = "completed"
            elif event.starts_at <= now:
                new_status = "ongoing"
            else:
                continue
            if new_status != event.status:
                cls.objects.filter(pk=event.pk).update(status=new_status)

    @property
    def starts_at(self):
        return timezone.make_aware(datetime.combine(self.date, self.time))

    @property
    def ends_at(self):
        """Explicit end, or the end of the last event day when no end time was given."""
        end_date = self.end_date or self.date
        end_time = self.end_time or time(23, 59, 59)
        return timezone.make_aware(datetime.combine(end_date, end_time))

    @property
    def has_ended(self):
        return self.status == "completed" or self.ends_at <= timezone.now()

    @property
    def rule_list(self):
        return [line.strip().lstrip("-•*").strip() for line in self.rules.splitlines() if line.strip()]

    @property
    def has_coordinators(self):
        return any(
            [
                self.student_coordinator_name,
                self.student_coordinator_phone,
                self.teacher_coordinator_name,
                self.teacher_coordinator_phone,
            ]
        )

    @property
    def registered_count(self):
        return self.registrations.count()

    @property
    def seats_left(self):
        return max(self.max_participants - self.registered_count, 0)

    @property
    def is_full(self):
        return self.registered_count >= self.max_participants

    @property
    def is_open(self):
        return self.status in ("upcoming", "ongoing") and not self.is_full and not self.has_ended

    @property
    def category_icon(self):
        return CATEGORY_ICONS.get(self.category, "bi-stars")

    @property
    def occupancy_percent(self):
        if self.max_participants == 0:
            return 0
        return min(int((self.registered_count / self.max_participants) * 100), 100)


class Registration(models.Model):
    TYPE_CHOICES = [
        ("solo", "Solo"),
        ("team", "Team"),
    ]

    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="event_registrations")
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="registrations")
    participation_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default="solo")
    team_name = models.CharField(max_length=100, blank=True)
    team_members = models.TextField(blank=True, help_text="One player name per line.")
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "event")
        ordering = ["-registered_at"]

    def __str__(self):
        return f"{self.student.username} → {self.event.title}"

    @property
    def member_list(self):
        return [name.strip() for name in self.team_members.splitlines() if name.strip()]
