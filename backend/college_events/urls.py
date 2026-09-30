from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "College Events Administration"
admin.site.site_title = "Events Admin"
admin.site.index_title = "Manage College Events"

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("", include("events.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
