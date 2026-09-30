"""
WSGI config for college_events project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project_settings")

try:
    from django.core.wsgi import get_wsgi_application

    application = get_wsgi_application()
except Exception:
    _startup_error = traceback.format_exc()
    print(_startup_error, file=sys.stderr)

    def application(environ, start_response):
        start_response("500 Internal Server Error", [("Content-Type", "text/plain; charset=utf-8")])
        return [("Application failed to start:\n\n" + _startup_error).encode()]
