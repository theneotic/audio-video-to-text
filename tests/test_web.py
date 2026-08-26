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
    assert "Make a record" in response.text
    assert "Whisper model" in response.text
    assert "cdn.tailwindcss.com" in response.text
    assert 'hx-post="/transcribe"' in response.text
    assert 'hx-target="#app-panel"' in response.text
    assert 'id="speech-panel"' in response.text
    assert 'id="transcription-form"' in response.text
    assert 'transcribe.js' in response.text
    assert 'id="upload-status"' in response.text
    assert 'action="/speak"' in response.text
    assert 'vendor/espeakng/espeakng.js' in response.text
    assert 'speech.js' in response.text
    assert 'id="listen-speech"' in response.text
    assert 'id="speech-player"' in response.text
    assert "LOCAL ONLY" in response.text


def test_standard_site_pages_render(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path))
    pages = {
        "/about": "A quieter way to",
        "/contact": "Have a question?",
        "/privacy": "Keep a clear",
        "/terms": "Use it well.",
    }
    for path, heading in pages.items():
        response = client.get(path)
        assert response.status_code == 200
        assert heading in response.text
        assert 'href="/privacy"' in response.text
        assert 'href="/terms"' in response.text
        assert "© 2026 theneotic" in response.text


def test_browser_speech_assets_are_served(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path))
    for path, marker in {
        "/static/speech.js": "SpeechSynthesisUtterance",
        "/static/vendor/espeakng/espeakng.js": "function eSpeakNG",
        "/static/vendor/espeakng/espeakng.worker.js": "eSpeakNGWorker",
    }.items():
        response = client.get(path)
        assert response.status_code == 200
        assert marker in response.text


def test_private_speech_download_returns_audio(tmp_path: Path, monkeypatch) -> None:
    import media_to_text.web as web

    def fake_speech(*args, **kwargs) -> bytes:
        assert args[0] == "Hello from the private speech engine."
        assert kwargs["voice"] == "en"
        assert kwargs["audio_format"] == "mp3"
        return b"fake-mp3"

    monkeypatch.setattr(web, "synthesize_speech", fake_speech)
    client = TestClient(create_app(tmp_path))
    response = client.post(
        "/speak",
        data={
            "text": "Hello from the private speech engine.",
            "voice": "en",
            "speed": "175",
            "pitch": "50",
            "audio_format": "mp3",
        },
    )
    assert response.status_code == 200
    assert response.content == b"fake-mp3"
    assert response.headers["content-type"] == "audio/mpeg"
    assert "media-to-text-speech.mp3" in response.headers["content-disposition"]
    assert response.headers["cache-control"] == "no-store"


def test_private_speech_rejects_empty_text(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path))
    response = client.post("/speak", data={"text": "", "audio_format": "mp3"})
    assert response.status_code == 400
    assert "Please enter some text to speak." in response.text


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
        data={
            "original_filename": "interview.mp4",
            "model": "tiny",
            "output_format": "all",
            "language": "en",
        },
    )
    assert response.status_code == 200
    assert "Hello from the browser." in response.text
    assert "interview.mp4" in response.text
    assert "/download/" in response.text
    assert "<!doctype html>" not in response.text
    assert len(list(tmp_path.glob("*/transcript.*"))) == 4


def test_invalid_download_returns_404(tmp_path: Path) -> None:
    client = TestClient(create_app(tmp_path))
    response = client.get("/download/not-a-job/transcript.txt")
    assert response.status_code == 404


def test_vercel_uses_writable_tmp_job_directory(monkeypatch) -> None:
    monkeypatch.delenv("MEDIA_TO_TEXT_JOB_ROOT", raising=False)
    monkeypatch.setenv("VERCEL", "1")
    app = create_app()
    assert app.state.job_root == Path("/tmp/media_to_text_jobs")
