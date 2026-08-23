"""Local audio and video transcription with Faster-Whisper."""

from .core import Segment, TranscriptionResult, Word, serialize, transcribe_file, write_outputs

__all__ = [
    "Segment",
    "TranscriptionResult",
    "Word",
    "serialize",
    "transcribe_file",
    "write_outputs",
]

__version__ = "0.1.0"
