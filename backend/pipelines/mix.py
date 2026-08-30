import os
from typing import List, Optional

from pydub import AudioSegment
from pydub.effects import normalize

from backend.schemas import Track


def mix_and_master(
    tracks: List[Track],
    output_path: str,
    fallback_audio_path: Optional[str] = None,
) -> str:
    """
    Mix audio tracks with volume/pan and apply simple mastering.
    If no audio tracks available, use fallback audio path.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    audio_tracks = [t for t in tracks if t.type == "audio" and os.path.exists(t.path)]

    if not audio_tracks:
        if fallback_audio_path and os.path.exists(fallback_audio_path):
            audio = AudioSegment.from_wav(fallback_audio_path)
            audio = normalize(audio)
            audio.export(output_path, format="wav")
            return output_path
        raise ValueError("No audio tracks or fallback audio available for export")

    # Find longest track duration
    max_duration_ms = 0
    segments = []
    for track in audio_tracks:
        seg = AudioSegment.from_wav(track.path)
        # Apply volume (0-1 -> dB)
        volume_db = max(-60, 20 * (track.volume - 1))
        seg = seg + volume_db
        # Apply pan (-1 left, 0 center, 1 right)
        seg = seg.pan(track.pan)
        segments.append(seg)
        max_duration_ms = max(max_duration_ms, len(seg))

    # Create silent base
    mixed = AudioSegment.silent(duration=max_duration_ms)
    for seg in segments:
        mixed = mixed.overlay(seg)

    # Mastering: normalize
    mixed = normalize(mixed)

    mixed.export(output_path, format="wav")
    return output_path
