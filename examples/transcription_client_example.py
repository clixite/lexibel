#!/usr/bin/env python3
"""Example client for LexiBel Audio Transcription API.

Demonstrates:
- Upload audio file
- Receive full transcript
- Extract AI insights (action items, decisions, references)
- Stream word-by-word results

Requirements:
    pip install httpx asyncio

Usage:
    python transcription_client_example.py meeting.mp3
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import httpx


class TranscriptionClient:
    """Client for LexiBel transcription API."""

    def __init__(self, base_url: str, jwt_token: str):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {jwt_token}"}

    async def transcribe_audio(
        self,
        file_path: str,
        language: Optional[str] = None,
        enable_diarization: bool = True,
        extract_insights: bool = True,
        case_id: Optional[str] = None,
    ) -> dict:
        """Transcribe audio file with full AI insights.

        Args:
            file_path: Path to audio file (mp3, wav, m4a, etc.)
            language: ISO 639-1 code (fr, nl, en) or None for auto-detect
            enable_diarization: Detect speaker changes
            extract_insights: Extract action items, decisions, etc.
            case_id: Optional UUID to link transcript to case

        Returns:
            dict with 'transcription' and 'insights' keys
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        # Build form data
        data = {
            "enable_diarization": str(enable_diarization).lower(),
            "extract_insights": str(extract_insights).lower(),
        }
        if language:
            data["language"] = language
        if case_id:
            data["case_id"] = case_id

        # Upload file
        async with httpx.AsyncClient(timeout=300.0) as client:
            with open(file_path, "rb") as f:
                files = {"file": (path.name, f, "audio/mpeg")}
                response = await client.post(
                    f"{self.base_url}/api/v1/ai/transcribe",
                    headers=self.headers,
                    files=files,
                    data=data,
                )
                response.raise_for_status()
                return response.json()

    async def transcribe_streaming(
        self,
        file_path: str,
        language: Optional[str] = None,
    ):
        """Stream transcription word-by-word.

        Yields:
            dict with 'word', 'start', 'end', 'confidence' keys
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Audio file not found: {file_path}")

        data = {}
        if language:
            data["language"] = language

        async with httpx.AsyncClient(timeout=300.0) as client:
            with open(file_path, "rb") as f:
                files = {"file": (path.name, f, "audio/mpeg")}
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/v1/ai/transcribe/stream",
                    headers=self.headers,
                    files=files,
                    data=data,
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.strip():
                            yield json.loads(line)


async def main():
    """Example usage."""
    # Configuration
    BASE_URL = "http://localhost:8000"
    JWT_TOKEN = "your-jwt-token-here"  # Get from login endpoint

    if len(sys.argv) < 2:
        print("Usage: python transcription_client_example.py <audio_file.mp3>")
        sys.exit(1)

    audio_file = sys.argv[1]

    # Initialize client
    client = TranscriptionClient(BASE_URL, JWT_TOKEN)

    print(f"🎙️  Transcribing: {audio_file}")
    print("=" * 80)

    # Example 1: Full transcription with insights
    print("\n📝 Example 1: Full Transcription + AI Insights")
    print("-" * 80)
    try:
        result = await client.transcribe_audio(
            file_path=audio_file,
            language="fr",  # or None for auto-detect
            enable_diarization=True,
            extract_insights=True,
        )

        # Display transcript
        transcription = result["transcription"]
        print(f"\n✅ Transcription completed in {transcription['processing_time_seconds']:.1f}s")
        print(f"   Language: {transcription['language']}")
        print(f"   Duration: {transcription['duration_seconds']:.1f}s")
        print(f"   Confidence: {transcription['confidence_score']:.2%}")
        print(f"\n📄 Full Text:")
        print(transcription["full_text"])

        # Display speaker segments
        if transcription["segments"]:
            print(f"\n🗣️  Speaker Segments ({len(transcription['segments'])}):")
            for seg in transcription["segments"][:5]:  # Show first 5
                timestamp = f"[{seg['start_time']:.1f}s - {seg['end_time']:.1f}s]"
                print(f"   {seg['speaker_id']:12} {timestamp:20} {seg['text'][:60]}...")

        # Display insights
        if result.get("insights"):
            insights = result["insights"]
            print(f"\n💡 AI Insights")
            print("-" * 80)

            # Summary
            print(f"\n📋 Summary:")
            print(f"   {insights['summary']}")

            # Action items
            if insights["action_items"]:
                print(f"\n✅ Action Items ({len(insights['action_items'])}):")
                for action in insights["action_items"]:
                    assignee = f"@{action['assignee']}" if action["assignee"] else ""
                    deadline = f"⏰ {action['deadline']}" if action["deadline"] else ""
                    priority_emoji = {
                        "urgent": "🔴",
                        "high": "🟠",
                        "medium": "🟡",
                        "low": "🟢",
                    }.get(action["priority"], "⚪")
                    print(f"   {priority_emoji} {action['text']} {assignee} {deadline}")

            # Decisions
            if insights["decisions"]:
                print(f"\n⚖️  Decisions Made ({len(insights['decisions'])}):")
                for dec in insights["decisions"]:
                    who = f"by {dec['decided_by']}" if dec["decided_by"] else ""
                    print(f"   • {dec['text']} {who}")

            # References
            if insights["references"]:
                print(f"\n🔗 References Detected ({len(insights['references'])}):")
                ref_types = {"case": "📁", "contact": "👤", "document": "📄", "law": "⚖️"}
                for ref in insights["references"][:5]:  # Show first 5
                    emoji = ref_types.get(ref["ref_type"], "🔗")
                    print(f"   {emoji} [{ref['ref_type']}] {ref['text']}")

            # Sentiment & Urgency
            sentiment_emoji = "😊" if insights["sentiment_score"] > 0.3 else "😐" if insights["sentiment_score"] > -0.3 else "😟"
            urgency_emoji = {"critical": "🚨", "high": "⚠️", "normal": "✅", "low": "🟢"}.get(insights["urgency_level"], "✅")
            print(f"\n📊 Analysis:")
            print(f"   Sentiment: {sentiment_emoji} {insights['sentiment_score']:+.2f}")
            print(f"   Urgency: {urgency_emoji} {insights['urgency_level']}")
            print(f"   Topics: {', '.join(insights['key_topics'][:5])}")

            # Suggested actions
            if insights["suggested_next_actions"]:
                print(f"\n🎯 Suggested Next Actions:")
                for action in insights["suggested_next_actions"]:
                    print(f"   {action}")

    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP Error: {e.response.status_code}")
        print(f"   {e.response.json()['detail']}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Example 2: Streaming transcription
    print("\n\n📡 Example 2: Streaming Transcription")
    print("-" * 80)
    print("Words as they appear:")
    try:
        word_count = 0
        async for word_data in client.transcribe_streaming(
            file_path=audio_file, language="fr"
        ):
            if "error" in word_data:
                print(f"\n❌ Error: {word_data['error']}")
                break

            # Print words inline
            print(word_data["word"], end=" ", flush=True)
            word_count += 1

            # Show confidence occasionally
            if word_count % 10 == 0:
                print(f"(conf: {word_data['confidence']:.2f})", end=" ", flush=True)

        print(f"\n\n✅ Streamed {word_count} words")

    except Exception as e:
        print(f"\n❌ Streaming Error: {e}")

    print("\n" + "=" * 80)
    print("✨ Done!")


if __name__ == "__main__":
    asyncio.run(main())
