from datetime import time, timedelta

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .forms import DATETIME_LOCAL, EventForm, StudentRegisterForm
from .models import Event, Registration, StudentProfile


def signup_data(**overrides):
    data = {
        "first_name": "Asha",
        "last_name": "Rao",
        "email": "asha@college.edu",
        "phone": "98450 12345",
        "roll_number": "bca2024001",
        "department": "BCA",
        "year": "2",
        "username": "asha",
        "password": "secret12",
        "confirm_password": "secret12",
    }
    data.update(overrides)
    return data


class HomeSliderTests(TestCase):
    def test_home_slider_shows_every_open_event(self):
        admin = User.objects.create_user("admin", password="x", is_staff=True)
        for days in (1, 2, 3):
            Event.objects.create(
                title=f"Event {days}", description="d", category="seminar", venue="v",
                date=timezone.localdate() + timedelta(days=days), time=time(10, 0), created_by=admin,
            )
        response = self.client.get(reverse("home"))
        self.assertContains(response, 'class="spotlight slide', count=3)
        self.assertContains(response, "data-index=", count=3)
        self.assertContains(response, "Next up", count=1)
        self.assertContains(response, 'spotlight-label soon"', count=2)


class PosterStorageTests(TestCase):
    def test_poster_is_stored_in_mongodb_and_served(self):
        name = default_storage.save("event_posters/test.png", ContentFile(b"\x89PNG-bytes", name="test.png"))
        try:
            self.assertTrue(default_storage.exists(name))
            response = self.client.get(default_storage.url(name))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, b"\x89PNG-bytes")
            self.assertEqual(response["Content-Type"], "image/png")
        finally:
            default_storage.delete(name)
        self.assertFalse(default_storage.exists(name))
        self.assertEqual(self.client.get(default_storage.url(name)).status_code, 404)


class StudentSignupTests(TestCase):
    def test_signup_creates_profile_and_logs_in(self):
        response = self.client.post(reverse("student_register"), signup_data())
        self.assertRedirects(response, reverse("student_dashboard"))
        profile = StudentProfile.objects.get(user__username="asha")
        self.assertEqual(profile.phone, "9845012345")
        self.assertEqual(profile.roll_number, "BCA2024001")
        self.assertEqual(len(mail.outbox), 1)
        welcome = mail.outbox[0]
        self.assertEqual(welcome.to, ["asha@college.edu"])
        self.assertIn("Welcome", welcome.subject)
        self.assertIn("Dear Asha Rao,", welcome.body)
        self.assertIn("Thank you for signing up with Srinivas University Events!", welcome.body)
        self.assertIn("Email       : asha@college.edu", welcome.body)
        self.assertIn(timezone.localdate().strftime("%d %B %Y"), welcome.body)

    def test_invalid_phone_and_short_password_are_rejected(self):
        form = StudentRegisterForm(data=signup_data(phone="12345", password="abc", confirm_password="abc"))
        self.assertFalse(form.is_valid())
        self.assertIn("phone", form.errors)
        self.assertIn("password", form.errors)

    def test_roll_number_with_symbols_shows_error_instead_of_crashing(self):
        response = self.client.post(reverse("student_register"), signup_data(roll_number="BCA(2024"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Use only letters, numbers")

    def test_duplicate_roll_number_is_case_insensitive(self):
        self.client.post(reverse("student_register"), signup_data())
        self.client.logout()
        form = StudentRegisterForm(
            data=signup_data(roll_number="BCA2024001", username="asha2", email="asha2@college.edu")
        )
        self.assertFalse(form.is_valid())
        self.assertIn("roll_number", form.errors)

    def test_student_and_admin_logins_send_welcome_banner(self):
        User.objects.create_user("stu", email="stu@college.edu", password="secret12", first_name="Stu")
        User.objects.create_user("boss", email="boss@college.edu", password="secret12", is_staff=True)
        self.client.post(
            reverse("login"), {"username": "stu", "password": "secret12"},
            HTTP_USER_AGENT="Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 Chrome/120.0 Safari/537.36",
        )
        self.client.logout()
        self.client.post(reverse("login"), {"username": "boss", "password": "secret12"})
        self.assertEqual([m.to for m in mail.outbox], [["stu@college.edu"], ["boss@college.edu"]])
        student_alert, admin_alert = mail.outbox
        self.assertIn("first sign-in", student_alert.subject)
        self.assertIn("Google Chrome on Windows", student_alert.body)
        self.assertIn("Role       : Student", student_alert.body)
        self.assertIn("Role       : Administrator", admin_alert.body)
        self.assertIn("Open admin dashboard", admin_alert.body)

    def test_login_email_is_sent_only_on_first_login(self):
        User.objects.create_user("boss", email="boss@college.edu", password="secret12", is_staff=True)
        self.client.post(reverse("student_register"), signup_data())
        self.client.logout()
        for _ in range(2):
            self.client.post(reverse("login"), {"username": "asha", "password": "secret12"})
            self.client.logout()
            self.client.post(reverse("login"), {"username": "boss", "password": "secret12"})
            self.client.logout()
        subjects = [(m.to, m.subject) for m in mail.outbox]
        self.assertEqual(len(subjects), 3)
        self.assertIn("Welcome", subjects[0][1])
        self.assertEqual([to for to, _ in subjects[1:]], [["asha@college.edu"], ["boss@college.edu"]])
        self.assertTrue(all("first sign-in" in s for _, s in subjects[1:]))

    @override_settings(
        LOGIN_ALERT_ROLES={"student"},
        EMAIL_BRAND={**settings.EMAIL_BRAND, "portal": "Demo Campus Events"},
    )
    def test_login_alert_roles_and_branding_come_from_settings(self):
        User.objects.create_user("stu", email="stu@college.edu", password="secret12")
        User.objects.create_user("boss", email="boss@college.edu", password="secret12", is_staff=True)
        self.client.post(reverse("login"), {"username": "boss", "password": "secret12"})
        self.assertEqual(len(mail.outbox), 0)
        self.client.logout()
        self.client.post(reverse("login"), {"username": "stu", "password": "secret12"})
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Demo Campus Events", mail.outbox[0].subject)

    def test_signup_page_hides_sidebar(self):
        response = self.client.get(reverse("student_register"))
        self.assertContains(response, "auth-layout")
        self.assertNotContains(response, 'id="sidebar"')


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
