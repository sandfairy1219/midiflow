import { useState } from "react";

interface Props {
  onGenerate: (prompt: string, duration: number) => void;
  isGenerating: boolean;
}

export function PromptPanel({ onGenerate, isGenerating }: Props) {
  const [prompt, setPrompt] = useState("lofi hip hop beat, piano and drums");
  const [duration, setDuration] = useState(10);

  return (
    <div style={{ padding: 16, border: "1px solid #ccc", borderRadius: 8, marginBottom: 16 }}>
      <h3>Generate Music</h3>
      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        rows={3}
        style={{ width: "100%", marginBottom: 8 }}
      />
      <div style={{ marginBottom: 8 }}>
        <label>Duration: {duration}s </label>
        <input
          type="range"
          min={3}
          max={30}
          value={duration}
          onChange={(e) => setDuration(Number(e.target.value))}
        />
      </div>
      <button onClick={() => onGenerate(prompt, duration)} disabled={isGenerating}>
        {isGenerating ? "Generating..." : "Generate"}
      </button>
    </div>
  );
}
