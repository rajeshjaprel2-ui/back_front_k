import re
from datetime import datetime

from django import forms
from django.contrib.auth.models import User
from django.utils import timezone

from .models import Event, StudentProfile, team_sport_size

PHONE_RE = re.compile(r"^(\+91[\s-]?)?[6-9]\d{9}$")
ROLL_RE = re.compile(r"^[A-Za-z0-9/-]{3,20}$")


def _clean_student_phone(value):
    phone = re.sub(r"[\s-]", "", value)
    if not PHONE_RE.match(phone):
        raise forms.ValidationError("Enter a valid 10-digit mobile number.")
    return phone


def _clean_roll_number(value, exclude_pk=None):
    entered = value.strip()
    if not ROLL_RE.match(entered):
        raise forms.ValidationError("Use only letters, numbers, '/' or '-' (e.g. BCA2024001).")
    roll = entered.upper()
    # iexact compiles to an unescaped MongoDB regex, so "(" or "[" in a roll number would crash the query.
    taken = StudentProfile.objects.filter(roll_number__in={roll, entered})
    if exclude_pk:
        taken = taken.exclude(pk=exclude_pk)
    if taken.exists():
        raise forms.ValidationError("This roll number is already registered.")
    return roll


class SkyFormMixin:
    def _style(self):
        for field in self.fields.values():
            css = "form-control"
            if isinstance(field.widget, (forms.Select, forms.SelectMultiple)):
                css = "form-select"
            if isinstance(field.widget, forms.CheckboxInput):
                css = "form-check-input"
            if isinstance(field.widget, forms.FileInput):
                css = "form-control"
            existing = field.widget.attrs.get("class", "")
            field.widget.attrs["class"] = f"{existing} {css}".strip()

    def full_clean(self):
        super().full_clean()
        for name in self.errors:
            if name in self.fields:
                attrs = self.fields[name].widget.attrs
                attrs["class"] = f"{attrs.get('class', '')} is-invalid".strip()


class StudentRegisterForm(SkyFormMixin, forms.ModelForm):
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)
    email = forms.EmailField()
    username = forms.CharField(max_length=150)
    password = forms.CharField(
        widget=forms.PasswordInput,
        min_length=6,
        error_messages={"min_length": "Password must be at least 6 characters."},
    )
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = StudentProfile
        fields = ["roll_number", "department", "year", "phone"]
        widgets = {"year": forms.RadioSelect}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()
        self.fields["year"].widget.attrs.pop("class", None)
        self.fields["year"].choices = StudentProfile.YEAR_CHOICES
        self.fields["department"].choices = [("", "Select department")] + StudentProfile.DEPARTMENT_CHOICES
        self.fields["email"].widget.attrs["autocomplete"] = "email"
        self.fields["username"].widget.attrs["autocomplete"] = "username"
        self.fields["password"].widget.attrs["autocomplete"] = "new-password"
        self.fields["confirm_password"].widget.attrs["autocomplete"] = "new-password"
        self.fields["phone"].widget.input_type = "tel"
        self.fields["phone"].widget.attrs.update({"inputmode": "numeric", "maxlength": "13"})
        self.fields["first_name"].widget.attrs["placeholder"] = "First name"
        self.fields["last_name"].widget.attrs["placeholder"] = "Last name"
        self.fields["email"].widget.attrs["placeholder"] = "college@email.com"
        self.fields["username"].widget.attrs["placeholder"] = "Choose a username"
        self.fields["password"].widget.attrs["placeholder"] = "Minimum 6 characters"
        self.fields["confirm_password"].widget.attrs["placeholder"] = "Re-enter password"
        self.fields["roll_number"].widget.attrs["placeholder"] = "e.g. BCA2024001"
        self.fields["phone"].widget.attrs["placeholder"] = "10-digit mobile number"

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean_phone(self):
        return _clean_student_phone(self.cleaned_data["phone"])

    def clean_roll_number(self):
        return _clean_roll_number(self.cleaned_data["roll_number"])

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") != cleaned.get("confirm_password"):
            self.add_error("confirm_password", "Passwords do not match.")
        return cleaned

    def save(self, commit=True):
        user = User.objects.create_user(
            username=self.cleaned_data["username"],
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password"],
            first_name=self.cleaned_data["first_name"],
            last_name=self.cleaned_data["last_name"],
        )
        profile = super().save(commit=False)
        profile.user = user
        if commit:
            profile.save()
        return profile


class UserEditForm(SkyFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True
        self._style()

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("This email is already registered.")
        return email


class StudentProfileEditForm(SkyFormMixin, forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ["roll_number", "department", "year", "phone"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()
        self.fields["phone"].widget.input_type = "tel"

    def clean_phone(self):
        return _clean_student_phone(self.cleaned_data["phone"])

    def clean_roll_number(self):
        return _clean_roll_number(self.cleaned_data["roll_number"], exclude_pk=self.instance.pk)


class LoginForm(SkyFormMixin, forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._style()
        self.fields["username"].widget.attrs.update(
            {"placeholder": "Enter your username", "autocomplete": "username", "autofocus": True}
        )
        self.fields["password"].widget.attrs.update(
            {"placeholder": "Enter your password", "autocomplete": "current-password"}
        )


DATETIME_LOCAL = "%Y-%m-%dT%H:%M"


def _datetime_local_field(required):
    return forms.DateTimeField(
        required=required,
        input_formats=[DATETIME_LOCAL],
        widget=forms.DateTimeInput(attrs={"type": "datetime-local"}, format=DATETIME_LOCAL),
    )


class EventForm(SkyFormMixin, forms.ModelForm):
    starts_at = _datetime_local_field(required=True)
    ends_at = _datetime_local_field(required=False)

    class Meta:
        model = Event
        fields = [
            "title",
            "description",
            "category",
            "venue",
            "max_participants",
            "participation_type",
            "max_team_size",
            "rules",
            "student_coordinator_name",
            "student_coordinator_phone",
            "teacher_coordinator_name",
            "teacher_coordinator_phone",
            "poster",
            "status",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "rules": forms.Textarea(attrs={"rows": 6}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        event = self.instance
        if event.pk:
            self.initial["starts_at"] = datetime.combine(event.date, event.time)
            if event.end_date or event.end_time:
                self.initial["ends_at"] = datetime.combine(
                    event.end_date or event.date, event.end_time or event.time
                )
        self._style()
        for name in (
            "rules",
            "student_coordinator_name",
            "student_coordinator_phone",
            "teacher_coordinator_name",
            "teacher_coordinator_phone",
        ):
            self.fields[name].required = True
        self.fields["title"].widget.attrs["placeholder"] = "Event title"
        self.fields["venue"].widget.attrs["placeholder"] = "e.g. Seminar Hall, Block A"
        self.fields["rules"].widget.attrs["placeholder"] = (
            "One rule per line, e.g.\nCarry your college ID card.\nReport 30 minutes before the start time."
        )
        self.fields["student_coordinator_name"].widget.attrs["placeholder"] = "Student coordinator's full name"
        self.fields["teacher_coordinator_name"].widget.attrs["placeholder"] = "Faculty coordinator's full name"
        for name in ("student_coordinator_phone", "teacher_coordinator_phone"):
            self.fields[name].widget.input_type = "tel"
            self.fields[name].widget.attrs["placeholder"] = "10-digit mobile number"
        self.fields["category"].choices = [("", "Select a category")] + list(Event.CATEGORY_CHOICES)
        if not self._starts_in_past():
            self.fields["starts_at"].widget.attrs["min"] = timezone.localtime().strftime(DATETIME_LOCAL)

    def _starts_in_past(self):
        """Editing an event that already started keeps its original date selectable."""
        event = self.instance
        return bool(event.pk and event.date and event.starts_at <= timezone.now())

    def _clean_phone(self, name):
        phone = re.sub(r"[\s-]", "", self.cleaned_data.get(name, ""))
        if phone and not PHONE_RE.match(phone):
            raise forms.ValidationError("Enter a valid 10-digit mobile number.")
        return phone

    def clean_student_coordinator_phone(self):
        return self._clean_phone("student_coordinator_phone")

    def clean_teacher_coordinator_phone(self):
        return self._clean_phone("teacher_coordinator_phone")

    def clean(self):
        cleaned = super().clean()
        starts_at, ends_at = cleaned.get("starts_at"), cleaned.get("ends_at")
        if starts_at and (not self.instance.pk or "starts_at" in self.changed_data):
            if starts_at < timezone.now().replace(second=0, microsecond=0):
                self.add_error("starts_at", "The event cannot start in the past. Pick today or a future date.")
        if starts_at and ends_at and ends_at <= starts_at:
            self.add_error("ends_at", "Until must be after the start date and time.")
        if cleaned.get("category") == "sports" and team_sport_size(cleaned.get("title")):
            cleaned["participation_type"] = "team"
        if cleaned.get("participation_type") in ("team", "both") and (cleaned.get("max_team_size") or 0) < 2:
            self.add_error("max_team_size", "A team needs at least 2 players.")
        return cleaned

    def save(self, commit=True):
        event = super().save(commit=False)
        starts_at = timezone.localtime(self.cleaned_data["starts_at"])
        event.date, event.time = starts_at.date(), starts_at.time()
        ends_at = self.cleaned_data.get("ends_at")
        if ends_at:
            ends_at = timezone.localtime(ends_at)
            event.end_date, event.end_time = ends_at.date(), ends_at.time()
        else:
            event.end_date = event.end_time = None
        if commit:
            event.save()
        return event
