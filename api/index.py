from pathlib import Path
import os
import sys

# Vercel's Python runtime imports file-based functions from the repository root.
# Add the existing src layout to Python's import path before loading the app.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Vercel functions can write only to the temporary filesystem.
os.environ.setdefault("MEDIA_TO_TEXT_JOB_ROOT", "/tmp/media_to_text_jobs")

from media_to_text.web import app  # noqa: E402,F401
