"""Vercel entrypoint for the Media to Text FastAPI application."""

from media_to_text.web import app

__all__ = ["app"]
