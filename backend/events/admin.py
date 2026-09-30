from django.contrib import admin

from .models import Event, Registration, StudentProfile


@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("roll_number", "user", "department", "year", "phone")
    search_fields = ("roll_number", "user__username", "user__first_name", "user__last_name")
    list_filter = ("department", "year")


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "date", "venue", "status", "max_participants")
    list_filter = ("category", "status", "date")
    search_fields = ("title", "venue", "description")


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ("student", "event", "registered_at")
    list_filter = ("event", "registered_at")
    search_fields = ("student__username", "event__title")
