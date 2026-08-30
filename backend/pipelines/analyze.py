import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Dict

import librosa
import numpy as np
import soundfile as sf
from basic_pitch.inference import predict


def separate_stems(audio_path: str, output_dir: str, model: str = "htdemucs") -> Dict[str, str]:
    """
    Separate audio into stems using Demucs.
    Returns a dict mapping stem name to audio file path.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Demucs CLI writes output to output_dir/model_name/
    cmd = [
        sys.executable, "-m", "demucs.separate",
        "-n", model,
        "--out", output_dir,
        "--filename", "{stem}.wav",
        audio_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)

    # htemucs produces: output_dir/htdemucs/{drums,bass,other,vocals}.wav
    model_output_dir = os.path.join(output_dir, model)
    stems = {}
    for stem_name in ["drums", "bass", "other", "vocals"]:
        path = os.path.join(model_output_dir, f"{stem_name}.wav")
        if os.path.exists(path):
            stems[stem_name] = path
    return stems


def audio_to_midi(audio_path: str, output_midi_path: str, min_note_length: float = 0.05) -> str:
    """
    Convert audio to MIDI using Basic Pitch.
    Returns path to MIDI file.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_midi_path)), exist_ok=True)
    model_output, midi_data, note_events = predict(audio_path)
    midi_data.write(output_midi_path)
    return output_midi_path


def midi_to_note_list(midi_path: str) -> List[Dict]:
    """
    Convert a MIDI file into a simple list of note dicts for the editor.
    """
    import pretty_midi
    pm = pretty_midi.PrettyMIDI(midi_path)
    notes = []
    for instrument in pm.instruments:
        for note in instrument.notes:
            notes.append({
                "pitch": int(note.pitch),
                "start": float(note.start),
                "end": float(note.end),
                "velocity": int(note.velocity),
                "instrument": int(instrument.program),
            })
    notes.sort(key=lambda x: x["start"])
    return notes


def analyze_audio(audio_path: str, project_dir: str) -> Dict:
    """
    Full analysis pipeline:
    1. Stem separation with Demucs
    2. Melody MIDI extraction with Basic Pitch from the 'other' stem
    3. Return paths and note data
    """
    stems_dir = os.path.join(project_dir, "stems")
    os.makedirs(stems_dir, exist_ok=True)

    stems = separate_stems(audio_path, stems_dir)

    # Use 'other' stem for melody extraction (usually contains lead instruments)
    melody_source = stems.get("other", audio_path)
    midi_path = os.path.join(project_dir, "extracted_melody.mid")
    audio_to_midi(melody_source, midi_path)

    notes = midi_to_note_list(midi_path)

    return {
        "stems": stems,
        "midi_path": midi_path,
        "notes": notes,
    }
