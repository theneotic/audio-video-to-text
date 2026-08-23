"""Vercel entrypoint for the Media to Text FastAPI application."""

from pathlib import Path
import sys

# Vercel loads this file from the repository root, while the application package
# lives under the src layout. Make that package directory importable explicitly.
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from media_to_text.web import app  # noqa: E402

__all__ = ["app"]
