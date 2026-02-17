"""Audio Transcription Service — Whisper API + Speaker Diarization.

Handles audio file processing with:
- Multi-format support (mp3, wav, m4a, ogg, webm)
- Streaming transcription
- Speaker diarization (who said what)
- Language auto-detection (FR, NL, EN)
- Chunked processing for large files
"""

import io
import os
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import AsyncIterator, BinaryIO, Optional

import httpx


@dataclass
class SpeakerSegment:
    """A segment of speech by a specific speaker."""

    speaker_id: str  # "SPEAKER_00", "SPEAKER_01", etc.
    start_time: float  # seconds
    end_time: float  # seconds
    text: str
    confidence: float = 0.0


@dataclass
class TranscriptWord:
    """Individual word with timing information for streaming."""

    word: str
    start_time: float
    end_time: float
    confidence: float = 0.0


@dataclass
class TranscriptionResult:
    """Complete transcription result with metadata."""

    transcript_id: str
    full_text: str
    language: str
    duration_seconds: float
    segments: list[SpeakerSegment] = field(default_factory=list)
    words: list[TranscriptWord] = field(default_factory=list)
    confidence_score: float = 0.0
    processing_time_seconds: float = 0.0
    model: str = "whisper-1"


# ── Supported audio formats ──

SUPPORTED_FORMATS = {
    "audio/mpeg",  # mp3
    "audio/wav",
    "audio/wave",
    "audio/x-wav",
    "audio/mp4",  # m4a
    "audio/x-m4a",
    "audio/ogg",
    "audio/webm",
    "audio/flac",
}

MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25MB (Whisper API limit)
CHUNK_SIZE_BYTES = 20 * 1024 * 1024  # 20MB chunks for large files


# ── Transcription Service ──


class TranscriptionService:
    """Handles audio transcription via OpenAI Whisper API.

    Supports:
    - Streaming results (word-by-word)
    - Large file chunking
    - Speaker diarization (via Whisper timestamps)
    - Language detection
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.base_url = base_url or os.getenv(
            "WHISPER_BASE_URL", "https://api.openai.com/v1"
        )
        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY must be set for transcription service"
            )

    async def transcribe_audio(
        self,
        audio_file: BinaryIO,
        filename: str,
        language: Optional[str] = None,
        enable_diarization: bool = True,
    ) -> TranscriptionResult:
        """Transcribe audio file using Whisper API.

        Args:
            audio_file: File-like object containing audio data
            filename: Original filename (for format detection)
            language: ISO 639-1 language code (fr, nl, en). Auto-detect if None.
            enable_diarization: Enable speaker diarization

        Returns:
            TranscriptionResult with full transcript and segments
        """
        start_time = datetime.now()
        transcript_id = str(uuid.uuid4())

        # Read audio data
        audio_data = audio_file.read()
        audio_size = len(audio_data)

        if audio_size > MAX_FILE_SIZE_BYTES:
            # Chunk large files
            return await self._transcribe_chunked(
                audio_data, filename, language, enable_diarization, transcript_id
            )

        # Single API call for small files
        result = await self._call_whisper_api(
            audio_data, filename, language, enable_diarization
        )

        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()

        return TranscriptionResult(
            transcript_id=transcript_id,
            full_text=result["text"],
            language=result.get("language", language or "unknown"),
            duration_seconds=result.get("duration", 0.0),
            segments=self._extract_segments(result.get("segments", [])),
            words=self._extract_words(result.get("words", [])),
            confidence_score=self._calculate_confidence(result),
            processing_time_seconds=processing_time,
            model=result.get("model", "whisper-1"),
        )

    async def transcribe_streaming(
        self,
        audio_file: BinaryIO,
        filename: str,
        language: Optional[str] = None,
    ) -> AsyncIterator[TranscriptWord]:
        """Stream transcription results word-by-word.

        Yields TranscriptWord objects as they are processed.
        """
        audio_data = audio_file.read()
        result = await self._call_whisper_api(
            audio_data, filename, language, enable_timestamps=True
        )

        # Yield words as they come
        for word_data in result.get("words", []):
            yield TranscriptWord(
                word=word_data["word"],
                start_time=word_data.get("start", 0.0),
                end_time=word_data.get("end", 0.0),
                confidence=word_data.get("confidence", 0.0),
            )

    async def _call_whisper_api(
        self,
        audio_data: bytes,
        filename: str,
        language: Optional[str] = None,
        enable_diarization: bool = False,
        enable_timestamps: bool = False,
    ) -> dict:
        """Call Whisper API with audio data."""
        async with httpx.AsyncClient(timeout=300.0) as client:
            # Prepare multipart form data
            files = {
                "file": (filename, io.BytesIO(audio_data), "audio/mpeg"),
            }
            data = {
                "model": "whisper-1",
                "response_format": "verbose_json",  # Get detailed response
            }

            if language:
                data["language"] = language

            if enable_timestamps or enable_diarization:
                data["timestamp_granularities"] = ["word", "segment"]

            response = await client.post(
                f"{self.base_url}/audio/transcriptions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                files=files,
                data=data,
            )
            response.raise_for_status()
            return response.json()

    async def _transcribe_chunked(
        self,
        audio_data: bytes,
        filename: str,
        language: Optional[str],
        enable_diarization: bool,
        transcript_id: str,
    ) -> TranscriptionResult:
        """Transcribe large audio file in chunks."""
        # For production: use pydub or ffmpeg to split audio intelligently
        # For now: simple byte-level chunking with overlap
        chunks = []
        chunk_size = CHUNK_SIZE_BYTES
        overlap = 1024 * 1024  # 1MB overlap to avoid cutting words

        offset = 0
        while offset < len(audio_data):
            chunk_end = min(offset + chunk_size, len(audio_data))
            chunk_data = audio_data[offset:chunk_end]

            result = await self._call_whisper_api(
                chunk_data,
                f"chunk_{offset}_{filename}",
                language,
                enable_diarization,
            )
            chunks.append(result)

            offset = chunk_end - overlap if chunk_end < len(audio_data) else chunk_end

        # Merge chunks
        return self._merge_chunks(chunks, transcript_id)

    def _merge_chunks(
        self, chunks: list[dict], transcript_id: str
    ) -> TranscriptionResult:
        """Merge multiple transcription chunks into single result."""
        full_text = " ".join(chunk["text"] for chunk in chunks)
        all_segments = []
        time_offset = 0.0

        for chunk in chunks:
            for segment in chunk.get("segments", []):
                # Adjust timestamps
                segment_copy = segment.copy()
                segment_copy["start"] += time_offset
                segment_copy["end"] += time_offset
                all_segments.append(segment_copy)

            # Update offset based on last segment end time
            if chunk.get("segments"):
                time_offset = chunk["segments"][-1].get("end", time_offset)

        return TranscriptionResult(
            transcript_id=transcript_id,
            full_text=full_text,
            language=chunks[0].get("language", "unknown") if chunks else "unknown",
            duration_seconds=time_offset,
            segments=self._extract_segments(all_segments),
            confidence_score=self._calculate_confidence(chunks[0] if chunks else {}),
        )

    def _extract_segments(self, raw_segments: list[dict]) -> list[SpeakerSegment]:
        """Extract speaker segments from Whisper response.

        Note: Whisper doesn't natively support diarization.
        This is a simplified implementation. For production, integrate
        with pyannote.audio or similar diarization models.
        """
        segments = []
        current_speaker = "SPEAKER_00"
        speaker_count = 0

        for seg in raw_segments:
            # Simple heuristic: long pause = speaker change
            # In production: use actual diarization model
            if seg.get("start", 0) - segments[-1].end_time > 2.0 if segments else False:
                speaker_count += 1
                current_speaker = f"SPEAKER_{speaker_count:02d}"

            segments.append(
                SpeakerSegment(
                    speaker_id=current_speaker,
                    start_time=seg.get("start", 0.0),
                    end_time=seg.get("end", 0.0),
                    text=seg.get("text", ""),
                    confidence=seg.get("avg_logprob", 0.0),
                )
            )

        return segments

    def _extract_words(self, raw_words: list[dict]) -> list[TranscriptWord]:
        """Extract word-level timestamps."""
        return [
            TranscriptWord(
                word=w.get("word", ""),
                start_time=w.get("start", 0.0),
                end_time=w.get("end", 0.0),
                confidence=w.get("probability", 0.0),
            )
            for w in raw_words
        ]

    def _calculate_confidence(self, result: dict) -> float:
        """Calculate overall confidence score from Whisper result."""
        # Whisper provides log probabilities
        # Convert to 0-1 scale
        avg_logprob = result.get("avg_logprob", -1.0)
        # Simple conversion (log prob is typically -0.5 to -1.5)
        confidence = max(0.0, min(1.0, 1.0 + avg_logprob))
        return confidence


# ── Convenience functions ──


async def transcribe_file(
    file_path: str,
    language: Optional[str] = None,
    enable_diarization: bool = True,
) -> TranscriptionResult:
    """Transcribe audio file from disk.

    Args:
        file_path: Path to audio file
        language: ISO 639-1 language code (optional)
        enable_diarization: Enable speaker detection

    Returns:
        TranscriptionResult
    """
    service = TranscriptionService()
    with open(file_path, "rb") as f:
        filename = os.path.basename(file_path)
        return await service.transcribe_audio(f, filename, language, enable_diarization)


def validate_audio_format(mime_type: str) -> bool:
    """Check if audio format is supported."""
    return mime_type in SUPPORTED_FORMATS


def estimate_processing_time(file_size_bytes: int) -> float:
    """Estimate transcription time in seconds.

    Whisper typically processes at ~0.2x real-time.
    """
    # Rough estimate: 1MB of audio ≈ 1 minute
    # Processing at 0.2x speed
    estimated_duration_minutes = file_size_bytes / (1024 * 1024)
    return estimated_duration_minutes * 60 * 0.2
