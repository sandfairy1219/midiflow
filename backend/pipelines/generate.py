import os
import torch
import scipy.io.wavfile
import numpy as np
from transformers import AutoProcessor, MusicgenForConditionalGeneration


# Singleton model cache
_models = {}
_processors = {}

# MusicGen models are trained on ~30s chunks
MAX_CHUNK_SECONDS = 30.0
TOKENS_PER_SECOND = 50
SAMPLING_RATE = 32000


def get_model_and_processor(model_name: str = "facebook/musicgen-small"):
    if model_name not in _models:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = MusicgenForConditionalGeneration.from_pretrained(model_name)
        model = model.to(device)
        processor = AutoProcessor.from_pretrained(model_name)
        _models[model_name] = model
        _processors[model_name] = processor
    return _models[model_name], _processors[model_name]


def _crossfade_concat(chunks: list, fade_samples: int) -> np.ndarray:
    """Concatenate audio chunks with a short crossfade between them."""
    if not chunks:
        return np.array([], dtype=np.float32)
    if len(chunks) == 1:
        return chunks[0]

    out = [chunks[0]]
    for chunk in chunks[1:]:
        prev = out[-1]
        if len(prev) < fade_samples or len(chunk) < fade_samples:
            out.append(chunk)
            continue
        # Crossfade tail of prev with head of chunk
        fade_prev = prev[-fade_samples:]
        fade_next = chunk[:fade_samples]
        alpha = np.linspace(0, 1, fade_samples, dtype=np.float32)
        mixed = fade_prev * (1 - alpha) + fade_next * alpha
        out[-1] = np.concatenate([prev[:-fade_samples], mixed])
        out.append(chunk[fade_samples:])
    return np.concatenate(out)


def _generate_chunk(
    model,
    processor,
    device,
    prompt: str,
    max_new_tokens: int,
    melody_audio: np.ndarray | None = None,
) -> np.ndarray:
    """Generate a single audio chunk."""
    if melody_audio is not None:
        inputs = processor(
            audio=melody_audio,
            text=[prompt],
            sampling_rate=SAMPLING_RATE,
            return_tensors="pt",
        )
    else:
        inputs = processor(text=[prompt], return_tensors="pt")

    inputs = {k: v.to(device) for k, v in inputs.items() if isinstance(v, torch.Tensor)}

    with torch.no_grad():
        audio_values = model.generate(**inputs, max_new_tokens=max_new_tokens)

    return audio_values[0, 0].cpu().numpy()


def generate_music(
    prompt: str,
    output_path: str,
    duration_seconds: float = 10.0,
    model_name: str = "facebook/musicgen-small",
) -> str:
    """
    Generate audio from text prompt and save to output_path.
    Longer durations are generated in 30s chunks and concatenated.
    """
    model, processor = get_model_and_processor(model_name)
    device = next(model.parameters()).device

    if duration_seconds <= MAX_CHUNK_SECONDS:
        max_new_tokens = int(duration_seconds * TOKENS_PER_SECOND)
        audio_data = _generate_chunk(model, processor, device, prompt, max_new_tokens)
    else:
        num_chunks = int(np.ceil(duration_seconds / MAX_CHUNK_SECONDS))
        chunk_tokens = int(MAX_CHUNK_SECONDS * TOKENS_PER_SECOND)
        chunks = []
        for _ in range(num_chunks):
            chunk = _generate_chunk(model, processor, device, prompt, chunk_tokens)
            chunks.append(chunk)
        fade_samples = int(0.1 * SAMPLING_RATE)
        audio_data = _crossfade_concat(chunks, fade_samples)
        # Trim to exact requested duration
        target_samples = int(duration_seconds * SAMPLING_RATE)
        audio_data = audio_data[:target_samples]

    sampling_rate = model.config.audio_encoder.sampling_rate
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    scipy.io.wavfile.write(output_path, rate=sampling_rate, data=audio_data)
    return output_path


def notes_to_melody_audio(notes, sampling_rate: int = SAMPLING_RATE, tempo: int = 120) -> np.ndarray:
    """
    Convert note dicts to a simple sine-wave melody audio for MusicGen conditioning.
    """
    import pretty_midi

    if not notes:
        max_end = 5.0
    else:
        max_end = max(n["end"] for n in notes)

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
        envelope = np.ones(length, dtype=np.float32)
        attack = min(500, length // 4)
        release = min(500, length // 4)
        envelope[:attack] = np.linspace(0, 1, attack)
        envelope[-release:] = np.linspace(1, 0, release)
        wave = 0.2 * np.sin(2 * np.pi * freq * t) * envelope
        audio[start_sample:end_sample] += wave

    peak = np.max(np.abs(audio))
    if peak > 0:
        audio = audio / peak * 0.5
    return audio


def _slice_notes_for_chunk(notes, chunk_index: int, chunk_duration: float):
    """Return notes shifted to chunk-local time for a given chunk."""
    chunk_start = chunk_index * chunk_duration
    chunk_end = chunk_start + chunk_duration
    sliced = []
    for note in notes:
        if note["end"] <= chunk_start or note["start"] >= chunk_end:
            continue
        sliced.append({
            **note,
            "start": max(0.0, note["start"] - chunk_start),
            "end": min(chunk_duration, note["end"] - chunk_start),
        })
    return sliced


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
    Long durations are chunked.
    """
    import librosa

    model, processor = get_model_and_processor(model_name)
    device = next(model.parameters()).device

    if not is_notes:
        melody_audio, _ = librosa.load(melody_input, sr=SAMPLING_RATE, mono=True)

    if duration_seconds <= MAX_CHUNK_SECONDS:
        if is_notes:
            melody_audio = notes_to_melody_audio(melody_input, sampling_rate=SAMPLING_RATE)
        melody_audio = melody_audio[: int(duration_seconds * SAMPLING_RATE)]
        max_new_tokens = int(duration_seconds * TOKENS_PER_SECOND)
        audio_data = _generate_chunk(model, processor, device, prompt, max_new_tokens, melody_audio)
    else:
        num_chunks = int(np.ceil(duration_seconds / MAX_CHUNK_SECONDS))
        chunk_tokens = int(MAX_CHUNK_SECONDS * TOKENS_PER_SECOND)
        chunks = []
        for i in range(num_chunks):
            if is_notes:
                chunk_notes = _slice_notes_for_chunk(melody_input, i, MAX_CHUNK_SECONDS)
                melody_audio = notes_to_melody_audio(chunk_notes, sampling_rate=SAMPLING_RATE)
            else:
                chunk_start = int(i * MAX_CHUNK_SECONDS * SAMPLING_RATE)
                chunk_end = chunk_start + int(MAX_CHUNK_SECONDS * SAMPLING_RATE)
                melody_audio = melody_audio[chunk_start:chunk_end]
            chunk = _generate_chunk(model, processor, device, prompt, chunk_tokens, melody_audio)
            chunks.append(chunk)
        fade_samples = int(0.1 * SAMPLING_RATE)
        audio_data = _crossfade_concat(chunks, fade_samples)
        target_samples = int(duration_seconds * SAMPLING_RATE)
        audio_data = audio_data[:target_samples]

    sampling_rate = model.config.audio_encoder.sampling_rate
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    scipy.io.wavfile.write(output_path, rate=sampling_rate, data=audio_data)
    return output_path
