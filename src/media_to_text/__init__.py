"""Local audio and video transcription with Faster-Whisper."""

from .core import Segment, TranscriptionResult, Word, serialize, transcribe_file, write_outputs
from .speech import synthesize_speech

__all__ = [
    "Segment",
    "TranscriptionResult",
    "Word",
    "serialize",
    "transcribe_file",
    "write_outputs",
    "synthesize_speech",
]

__version__ = "0.1.0"
