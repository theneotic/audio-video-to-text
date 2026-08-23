from pathlib import Path

from fastapi.testclient import TestClient

from media_to_text import Segment, TranscriptionResult
from media_to_text.web import create_app


def fake_result() -> TranscriptionResult:
    return TranscriptionResult(
        source="sample.wav",
        language="en",
        language_probability=0.98,
        duration=2.0,
        segments=(Segment(id=1, start=0.0, end=2.0, text="Hello from the browser."),),
    )


def test_home_page_renders(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path))
    response = client.get("/")
    assert response.status_code == 200
    assert "Your media." in response.text
    assert "Whisper model" in response.text
    assert "cdn.tailwindcss.com" in response.text
    assert 'hx-post="/transcribe"' in response.text
    assert 'hx-target="#app-panel"' in response.text


def test_invalid_extension_returns_helpful_error(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path))
    response = client.post(
        "/transcribe",
        files={"file": ("notes.pdf", b"not media", "application/pdf")},
        data={"model": "small", "output_format": "txt"},
    )
    assert response.status_code == 400
    assert "supported audio or video file" in response.text


def test_htmx_invalid_extension_returns_fragment(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path))
    response = client.post(
        "/transcribe",
        headers={"HX-Request": "true"},
        files={"file": ("notes.pdf", b"not media", "application/pdf")},
        data={"model": "small", "output_format": "txt"},
    )
    assert response.status_code == 400
    assert "That file needs another look." in response.text
    assert "<!doctype html>" not in response.text


def test_transcription_page_and_downloads_render(tmp_path: Path, monkeypatch) -> None:
    import media_to_text.web as web

    def fake_transcribe(*args, **kwargs) -> TranscriptionResult:
        return fake_result()

    monkeypatch.setattr(web, "transcribe_file", fake_transcribe)
    client = TestClient(create_app(tmp_path))
    response = client.post(
        "/transcribe",
        headers={"HX-Request": "true"},
        files={"file": ("sample.wav", b"fake audio", "audio/wav")},
        data={"model": "tiny", "output_format": "all", "language": "en"},
    )
    assert response.status_code == 200
    assert "Hello from the browser." in response.text
    assert "/download/" in response.text
    assert "<!doctype html>" not in response.text
    assert len(list(tmp_path.glob("*/transcript.*"))) == 4


def test_invalid_download_returns_404(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path))
    response = client.get("/download/not-a-job/transcript.txt")
    assert response.status_code == 404
