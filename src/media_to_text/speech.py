"""Offline text-to-speech helpers for the web application."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

MAX_SPEECH_CHARS = 10_000
SPEED_RANGE = (80, 400)
PITCH_RANGE = (0, 99)
DEFAULT_SPEED = 175
DEFAULT_PITCH = 50

# These are eSpeak NG voice identifiers, not remote provider voice names.
VOICE_OPTIONS = {
    "en": "English",
    "en-us": "English · US",
    "en-gb": "English · UK",
    "hi": "Hindi",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "it": "Italian",
    "pt": "Portuguese",
    "ja": "Japanese",
    "zh": "Chinese",
    "ta": "Tamil",
}
AUDIO_FORMATS = {"mp3": ("audio/mpeg", "mp3"), "wav": ("audio/wav", "wav")}


def _validated_text(text: str) -> str:
    value = text.strip()
    if not value:
        raise ValueError("Please enter some text to speak.")
    if len(value) > MAX_SPEECH_CHARS:
        raise ValueError(f"Please keep the speech text under {MAX_SPEECH_CHARS:,} characters.")
    return value


def _validated_integer(value: int, name: str, bounds: tuple[int, int]) -> int:
    minimum, maximum = bounds
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}.")
    return value


def _executable(name: str, install_hint: str) -> str:
    executable = shutil.which(name)
    if not executable:
        raise RuntimeError(f"{name} is not installed. {install_hint}")
    return executable


def synthesize_speech(
    text: str,
    *,
    voice: str = "en",
    speed: int = DEFAULT_SPEED,
    pitch: int = DEFAULT_PITCH,
    audio_format: str = "mp3",
) -> bytes:
    """Generate audio locally and return it as bytes.

    eSpeak NG writes a temporary WAV file. FFmpeg converts that file to MP3
    when requested. No text or audio leaves the machine running this app.
    """
    value = _validated_text(text)
    if voice not in VOICE_OPTIONS:
        raise ValueError("Please choose a supported speech language.")
    speed = _validated_integer(speed, "Speed", SPEED_RANGE)
    pitch = _validated_integer(pitch, "Pitch", PITCH_RANGE)
    if audio_format not in AUDIO_FORMATS:
        raise ValueError("Please choose MP3 or WAV output.")

    espeak = _executable(
        "espeak-ng",
        "Install the eSpeak NG package or use the Docker deployment provided by this project.",
    )
    with tempfile.TemporaryDirectory(prefix="media-to-text-speech-") as temporary_dir:
        directory = Path(temporary_dir)
        wav_path = directory / "speech.wav"
        command = [
            espeak,
            "--stdin",
            "-v",
            voice,
            "-s",
            str(speed),
            "-p",
            str(pitch),
            "-w",
            str(wav_path),
        ]
        process = subprocess.run(
            command,
            input=value,
            text=True,
            capture_output=True,
            check=False,
            timeout=60,
        )
        if process.returncode != 0 or not wav_path.is_file():
            detail = process.stderr.strip() or "eSpeak NG could not synthesize the supplied text."
            raise RuntimeError(detail)

        if audio_format == "wav":
            return wav_path.read_bytes()

        ffmpeg = _executable(
            "ffmpeg",
            "Install FFmpeg or use the Docker deployment provided by this project.",
        )
        mp3_path = directory / "speech.mp3"
        conversion = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(wav_path),
                "-codec:a",
                "libmp3lame",
                "-q:a",
                "4",
                str(mp3_path),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        if conversion.returncode != 0 or not mp3_path.is_file():
            detail = conversion.stderr.strip() or "FFmpeg could not create the MP3 file."
            raise RuntimeError(detail)
        return mp3_path.read_bytes()
