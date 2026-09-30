import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from college_events.settings import *  # noqa: E402,F401,F403

# Vercel resolves WSGI_APPLICATION to a file path relative to the repo root.
WSGI_APPLICATION = "project_wsgi.application"
