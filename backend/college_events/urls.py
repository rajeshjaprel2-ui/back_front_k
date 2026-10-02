from django.contrib import admin
from django.urls import include, path

from events.views import media_file

admin.site.site_header = "College Events Administration"
admin.site.site_title = "Events Admin"
admin.site.index_title = "Manage College Events"

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("media/<path:name>", media_file, name="media_file"),
    path("", include("events.urls")),
]
