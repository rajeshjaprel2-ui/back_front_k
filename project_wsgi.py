import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from college_events.wsgi import application  # noqa: E402,F401
