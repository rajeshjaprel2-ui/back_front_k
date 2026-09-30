from django.urls import path, register_converter

from . import views


class ObjectIdConverter:
    regex = "[0-9a-f]{24}"

    def to_python(self, value):
        return value

    def to_url(self, value):
        return str(value)


register_converter(ObjectIdConverter, "objectid")

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("register/", views.student_register, name="student_register"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("admin-panel/", views.admin_dashboard, name="admin_dashboard"),
    path("student-panel/", views.student_dashboard, name="student_dashboard"),
    path("events/", views.event_list, name="event_list"),
    path("events/create/", views.event_create, name="event_create"),
    path("events/<objectid:pk>/", views.event_detail, name="event_detail"),
    path("events/<objectid:pk>/edit/", views.event_edit, name="event_edit"),
    path("events/<objectid:pk>/delete/", views.event_delete, name="event_delete"),
    path("events/<objectid:pk>/register/", views.register_event, name="register_event"),
    path("events/<objectid:pk>/participants/", views.participants, name="participants"),
    path("events/<objectid:pk>/participants/export/", views.export_participants, name="export_participants"),
    path("registrations/<objectid:pk>/cancel/", views.cancel_registration, name="cancel_registration"),
    path("registrations/<objectid:pk>/remove/", views.participant_remove, name="participant_remove"),
    path("my-registrations/", views.my_registrations, name="my_registrations"),
    path("reports/", views.reports, name="reports"),
    path("students/", views.student_list, name="student_list"),
]
