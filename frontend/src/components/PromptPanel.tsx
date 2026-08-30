import { useState } from "react";

interface Props {
  onGenerate: (prompt: string, duration: number) => void;
  isGenerating: boolean;
}

const MAX_DURATION = 240; // 4 minutes

export function PromptPanel({ onGenerate, isGenerating }: Props) {
  const [prompt, setPrompt] = useState("lofi hip hop beat, piano and drums");
  const [duration, setDuration] = useState(10);

  const formatTime = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  return (
    <div className="card prompt-panel">
      <h3>Generate Music</h3>
      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        rows={3}
        placeholder="Describe the music you want..."
      />
      <div className="duration-row">
        <label>Duration</label>
        <input
          type="range"
          min={3}
          max={MAX_DURATION}
          step={1}
          value={duration}
          onChange={(e) => setDuration(Number(e.target.value))}
        />
        <span>{formatTime(duration)}</span>
      </div>
      <button onClick={() => onGenerate(prompt, duration)} disabled={isGenerating}>
        {isGenerating ? "Generating..." : "Generate"}
      </button>
    </div>
  );
}
