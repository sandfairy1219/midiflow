import os
import torch
import scipy.io.wavfile
from transformers import AutoProcessor, MusicgenForConditionalGeneration


# Singleton model cache
_models = {}
_processors = {}


def get_model_and_processor(model_name: str = "facebook/musicgen-small"):
    if model_name not in _models:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = MusicgenForConditionalGeneration.from_pretrained(model_name)
        model = model.to(device)
        processor = AutoProcessor.from_pretrained(model_name)
        _models[model_name] = model
        _processors[model_name] = processor
    return _models[model_name], _processors[model_name]


def generate_music(
    prompt: str,
    output_path: str,
    duration_seconds: float = 10.0,
    model_name: str = "facebook/musicgen-small",
) -> str:
    """
    Generate audio from text prompt and save to output_path.
    Returns the output path.
    """
    model, processor = get_model_and_processor(model_name)
    device = next(model.parameters()).device

    # MusicGen uses 50 tokens per second at 32kHz (small/medium)
    tokens_per_second = 50
    max_new_tokens = int(duration_seconds * tokens_per_second)

    inputs = processor(text=[prompt], return_tensors="pt")
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        audio_values = model.generate(**inputs, max_new_tokens=max_new_tokens)

    sampling_rate = model.config.audio_encoder.sampling_rate
    audio_data = audio_values[0, 0].cpu().numpy()

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    scipy.io.wavfile.write(output_path, rate=sampling_rate, data=audio_data)
    return output_path


def notes_to_melody_audio(notes, sampling_rate: int = 32000, tempo: int = 120) -> "np.ndarray":
    """
    Convert note dicts to a simple sine-wave melody audio for MusicGen conditioning.
    """
    import numpy as np
    import pretty_midi

    if not notes:
        max_end = 5.0
    else:
        max_end = max(n["end"] for n in notes)

    # Add a little tail silence
    duration = max_end + 1.0
    samples = int(duration * sampling_rate)
    audio = np.zeros(samples, dtype=np.float32)

    for note in notes:
        freq = pretty_midi.note_number_to_hz(note["pitch"])
        start_sample = int(note["start"] * sampling_rate)
        end_sample = min(int(note["end"] * sampling_rate), samples)
        length = max(0, end_sample - start_sample)
        if length == 0:
            continue
        t = np.arange(length) / sampling_rate
        # Gentle attack/release envelope
        envelope = np.ones(length, dtype=np.float32)
        attack = min(500, length // 4)
        release = min(500, length // 4)
        envelope[:attack] = np.linspace(0, 1, attack)
        envelope[-release:] = np.linspace(1, 0, release)
        wave = 0.2 * np.sin(2 * np.pi * freq * t) * envelope
        audio[start_sample:end_sample] += wave

    # Normalize
    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak * 0.5
    return audio


def generate_from_melody(
    prompt: str,
    melody_input,
    output_path: str,
    duration_seconds: float = 10.0,
    model_name: str = "facebook/musicgen-small",
    is_notes: bool = False,
) -> str:
    """
    Generate audio conditioned on a melody.
    melody_input can be a file path (str) or a list of note dicts if is_notes=True.
    """
    import librosa
    import numpy as np

    model, processor = get_model_and_processor(model_name)
    device = next(model.parameters()).device

    target_sr = 32000
    if is_notes:
        melody_audio = notes_to_melody_audio(melody_input, sampling_rate=target_sr)
    else:
        melody_audio, _ = librosa.load(melody_input, sr=target_sr, mono=True)

    melody_audio = melody_audio[: int(duration_seconds * target_sr)]
    # Pass 1D array; processor handles batching internally

    inputs = processor(
        audio=melody_audio,
        text=[prompt],
        sampling_rate=target_sr,
        return_tensors="pt",
    )
    inputs = {k: v.to(device) for k, v in inputs.items() if isinstance(v, torch.Tensor)}

    tokens_per_second = 50
    max_new_tokens = int(duration_seconds * tokens_per_second)

    with torch.no_grad():
        audio_values = model.generate(**inputs, max_new_tokens=max_new_tokens)

    sampling_rate = model.config.audio_encoder.sampling_rate
    audio_data = audio_values[0, 0].cpu().numpy()

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    scipy.io.wavfile.write(output_path, rate=sampling_rate, data=audio_data)
    return output_path
