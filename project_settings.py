import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from college_events.settings import *  # noqa: E402,F401,F403
