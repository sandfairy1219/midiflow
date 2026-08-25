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


def generate_from_melody(
    prompt: str,
    melody_path: str,
    output_path: str,
    duration_seconds: float = 10.0,
    model_name: str = "facebook/musicgen-small",
) -> str:
    """
    Generate audio conditioned on a melody audio file.
    This is the core 'edit -> regenerate' function.
    """
    import librosa
    import numpy as np

    model, processor = get_model_and_processor(model_name)
    device = next(model.parameters()).device

    # Load melody and resample to 32kHz (MusicGen expects this)
    target_sr = 32000
    melody, sr = librosa.load(melody_path, sr=target_sr, mono=True)
    melody = melody[: int(duration_seconds * target_sr)]
    melody = np.expand_dims(melody, axis=0)  # (1, samples)

    inputs = processor(
        audio=melody,
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
