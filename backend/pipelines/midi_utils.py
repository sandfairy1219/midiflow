import os
from typing import List, Dict

import pretty_midi


def notes_to_midi(notes: List[Dict], output_path: str, tempo: int = 120) -> str:
    """
    Save a list of note dicts to a MIDI file.
    Notes expected: {pitch, start, end, velocity, instrument}
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    pm = pretty_midi.PrettyMIDI(initial_tempo=tempo)

    # Group notes by instrument program
    instruments = {}
    for note_data in notes:
        program = int(note_data.get("instrument", 0))
        if program not in instruments:
            instruments[program] = pretty_midi.Instrument(program=program)
        note = pretty_midi.Note(
            velocity=int(note_data.get("velocity", 80)),
            pitch=int(note_data["pitch"]),
            start=float(note_data["start"]),
            end=float(note_data["end"]),
        )
        instruments[program].notes.append(note)

    for inst in instruments.values():
        pm.instruments.append(inst)

    pm.write(output_path)
    return output_path


def midi_to_notes(midi_path: str) -> List[Dict]:
    """Read a MIDI file and return note dicts."""
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
