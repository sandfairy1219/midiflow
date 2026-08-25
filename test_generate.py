import torch
from transformers import AutoProcessor, MusicgenForConditionalGeneration
import scipy.io.wavfile

model = MusicgenForConditionalGeneration.from_pretrained("facebook/musicgen-small")
processor = AutoProcessor.from_pretrained("facebook/musicgen-small")

device = "cuda" if torch.cuda.is_available() else "cpu"
model = model.to(device)

inputs = processor(
    text=["lofi hip hop beat, relaxing, piano and drums"],
    return_tensors="pt",
)
inputs = {k: v.to(device) for k, v in inputs.items()}

audio_values = model.generate(**inputs, max_new_tokens=256)

sampling_rate = model.config.audio_encoder.sampling_rate
scipy.io.wavfile.write("test_output.wav", rate=sampling_rate, data=audio_values[0, 0].cpu().numpy())
print("saved test_output.wav", "sampling_rate=", sampling_rate)
