from datetime import time, timedelta

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import DATETIME_LOCAL, EventForm
from .models import Event, Registration, StudentProfile


def form_data(**overrides):
    starts = timezone.localtime() + timedelta(days=2)
    data = {
        "title": "Seminar",
        "description": "About things",
        "category": "seminar",
        "venue": "Hall A",
        "max_participants": 50,
        "participation_type": "solo",
        "max_team_size": 4,
        "rules": "Carry ID card",
        "student_coordinator_name": "Rahul",
        "student_coordinator_phone": "9876543210",
        "teacher_coordinator_name": "Dr. Rao",
        "teacher_coordinator_phone": "9845012345",
        "status": "upcoming",
        "starts_at": starts.strftime(DATETIME_LOCAL),
    }
    data.update(overrides)
    return data


class EventFormTests(TestCase):
    def test_valid_future_event(self):
        self.assertTrue(EventForm(data=form_data()).is_valid())

    def test_past_start_date_is_rejected(self):
        yesterday = timezone.localtime() - timedelta(days=1)
        form = EventForm(data=form_data(starts_at=yesterday.strftime(DATETIME_LOCAL)))
        self.assertFalse(form.is_valid())
        self.assertIn("starts_at", form.errors)

    def test_rules_and_coordinators_are_required(self):
        form = EventForm(data=form_data(rules="", student_coordinator_name="", teacher_coordinator_phone=""))
        self.assertFalse(form.is_valid())
        self.assertIn("rules", form.errors)
        self.assertIn("student_coordinator_name", form.errors)
        self.assertIn("teacher_coordinator_phone", form.errors)

    def test_invalid_phone_is_rejected(self):
        form = EventForm(data=form_data(student_coordinator_phone="12345"))
        self.assertFalse(form.is_valid())
        self.assertIn("student_coordinator_phone", form.errors)

    def test_cricket_and_football_become_team_events(self):
        for title in ("Inter-College Cricket Trophy", "Football League"):
            form = EventForm(data=form_data(title=title, category="sports", participation_type="solo", max_team_size=11))
            self.assertTrue(form.is_valid(), form.errors)
            self.assertEqual(form.cleaned_data["participation_type"], "team")

    def test_chess_stays_solo(self):
        form = EventForm(data=form_data(title="Chess Championship", category="sports"))
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["participation_type"], "solo")


class EventEndTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user("admin", password="x", is_staff=True)
        self.student = User.objects.create_user("stu", password="x")
        StudentProfile.objects.create(user=self.student, roll_number="R1", department="BCA", year="1", phone="9876543210")
        today = timezone.localdate()
        self.past = Event.objects.create(
            title="Past Talk", description="d", category="seminar", venue="v",
            date=today - timedelta(days=3), time=time(10, 0), status="upcoming", created_by=self.admin,
        )
        self.future = Event.objects.create(
            title="Future Talk", description="d", category="seminar", venue="v",
            date=today + timedelta(days=3), time=time(10, 0), status="upcoming", created_by=self.admin,
        )

    def test_status_refreshes_to_completed(self):
        self.client.get(reverse("event_list"))
        self.past.refresh_from_db()
        self.future.refresh_from_db()
        self.assertEqual(self.past.status, "completed")
        self.assertEqual(self.future.status, "upcoming")

    def test_cannot_register_for_ended_event(self):
        self.client.login(username="stu", password="x")
        self.client.post(reverse("register_event", args=[self.past.pk]))
        self.assertFalse(Registration.objects.filter(event=self.past).exists())
        self.client.post(reverse("register_event", args=[self.future.pk]))
        self.assertTrue(Registration.objects.filter(event=self.future).exists())

    def test_registration_sends_confirmation_email(self):
        self.student.email = "stu@college.edu"
        self.student.save()
        self.client.login(username="stu", password="x")
        self.client.post(reverse("register_event", args=[self.future.pk]))
        self.assertEqual(len(mail.outbox), 1)
        sent = mail.outbox[0]
        self.assertEqual(sent.to, ["stu@college.edu"])
        self.assertIn("Future Talk", sent.subject)
        self.assertIn(self.future.date.strftime("%d %B %Y"), sent.body)
        self.assertIn("10:00 AM", sent.body)
        self.assertIn("Location : v", sent.body)

    def test_detail_shows_event_has_ended(self):
        response = self.client.get(reverse("event_detail", args=[self.past.pk]))
        self.assertContains(response, "Event Has Ended")
        self.assertNotContains(response, "Sign in to register")

    def test_list_shows_completed_section(self):
        response = self.client.get(reverse("event_list"))
        self.assertContains(response, "Completed events")
        self.assertContains(response, "Upcoming &amp; ongoing events")
