import { useState, useEffect } from "react";
import type { Project, Note } from "./types";
import {
  createProject,
  generateAudio,
  getJob,
  getProject,
  analyzeProject,
  saveMidi,
  regenerateAudio,
  exportProject,
} from "./api";
import { PromptPanel } from "./components/PromptPanel";
import { TrackList } from "./components/TrackList";
import { PianoRoll } from "./components/PianoRoll";

export function App() {
  const [project, setProject] = useState<Project | null>(null);
  const [status, setStatus] = useState<string>("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  useEffect(() => {
    createProject("New Session").then(setProject).catch((e) => setStatus(e instanceof Error ? e.message : String(e)));
  }, []);

  async function handleGenerate(prompt: string, duration: number) {
    if (!project) return;
    setIsGenerating(true);
    setStatus("Starting generation...");
    try {
      const job = await generateAudio(prompt, duration, project.project_id);
      setStatus(`Job ${job.job_id} running...`);

      while (true) {
        await new Promise((r) => setTimeout(r, 2000));
        const updated = await getJob(job.job_id);
        setStatus(`Job ${job.job_id}: ${updated.status}`);
        if (updated.status === "completed") {
          const refreshed = await getProject(project.project_id);
          setProject(refreshed);
          setStatus("Generation completed.");
          break;
        }
        if (updated.status === "failed") {
          setStatus(`Generation failed: ${updated.error_message}`);
          break;
        }
      }
    } catch (e: unknown) {
      setStatus(e instanceof Error ? e.message : String(e));
    } finally {
      setIsGenerating(false);
    }
  }

  async function handleAnalyze() {
    if (!project) return;
    setIsAnalyzing(true);
    setStatus("Starting analysis...");
    try {
      await analyzeProject(project.project_id);
      while (true) {
        await new Promise((r) => setTimeout(r, 3000));
        const refreshed = await getProject(project.project_id);
        setProject(refreshed);
        if (refreshed.tracks.length > 0) {
          setStatus("Analysis completed.");
          break;
        }
      }
    } catch (e: unknown) {
      setStatus(e instanceof Error ? e.message : String(e));
    } finally {
      setIsAnalyzing(false);
    }
  }

  const generatedFilename = project?.generated_audio?.split("\\").pop()?.split("/").pop();
  const notes = project?.midi_data?.notes || [];
  const [editedNotes, setEditedNotes] = useState<Note[]>(notes);
  const [regenPrompt, setRegenPrompt] = useState("rock remix, electric guitar and drums");
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  useEffect(() => {
    setEditedNotes(notes);
  }, [notes]);

  async function handleSaveMidi() {
    if (!project) return;
    setStatus("Saving MIDI...");
    try {
      const updated = await saveMidi(project.project_id, editedNotes);
      setProject(updated);
      setStatus("MIDI saved.");
    } catch (e: unknown) {
      setStatus(e instanceof Error ? e.message : String(e));
    }
  }

  async function handleRegenerate() {
    if (!project) return;
    setIsRegenerating(true);
    setStatus("Starting regeneration with melody...");
    try {
      const job = await regenerateAudio(project.project_id, regenPrompt, 10);
      while (true) {
        await new Promise((r) => setTimeout(r, 2000));
        const updated = await getJob(job.job_id);
        setStatus(`Regeneration ${job.job_id}: ${updated.status}`);
        if (updated.status === "completed") {
          const refreshed = await getProject(project.project_id);
          setProject(refreshed);
          setStatus("Regeneration completed.");
          break;
        }
        if (updated.status === "failed") {
          setStatus(`Regeneration failed: ${updated.error_message}`);
          break;
        }
      }
    } catch (e: unknown) {
      setStatus(e instanceof Error ? e.message : String(e));
    } finally {
      setIsRegenerating(false);
    }
  }

  async function handleExport() {
    if (!project) return;
    setIsExporting(true);
    setStatus("Exporting final mix...");
    try {
      const blob = await exportProject(project.project_id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `midiflow_${project.project_id}_final.wav`;
      a.click();
      URL.revokeObjectURL(url);
      setStatus("Export completed.");
    } catch (e: unknown) {
      setStatus(e instanceof Error ? e.message : String(e));
    } finally {
      setIsExporting(false);
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>MidiFlow</h1>
        <p className="status-bar">{status || "Ready"}</p>
      </header>

      <PromptPanel onGenerate={handleGenerate} isGenerating={isGenerating} />

      {project?.generated_audio && generatedFilename && (
        <div className="card">
          <h3>Generated Audio</h3>
          <audio
            controls
            src={`http://127.0.0.1:8000/audio/${project.project_id}/${generatedFilename}`}
            style={{ width: "100%" }}
          />
          <div style={{ marginTop: 12 }}>
            <button onClick={handleAnalyze} disabled={isAnalyzing} className="secondary">
              {isAnalyzing ? "Analyzing..." : "Analyze (Extract Stems + MIDI)"}
            </button>
          </div>
        </div>
      )}

      {editedNotes.length > 0 && (
        <div className="card">
          <h3>Piano Roll Editor</h3>
          <PianoRoll notes={editedNotes} onChange={setEditedNotes} />
          <div className="row wrap" style={{ marginBottom: 12 }}>
            <button onClick={handleSaveMidi}>Save Edited MIDI</button>
          </div>
          <div className="row wrap">
            <input
              type="text"
              value={regenPrompt}
              onChange={(e) => setRegenPrompt(e.target.value)}
              className="grow"
              placeholder="Style prompt for regeneration..."
            />
            <button onClick={handleRegenerate} disabled={isRegenerating}>
              {isRegenerating ? "Regenerating..." : "Regenerate with Melody"}
            </button>
          </div>
        </div>
      )}

      {project && (
        <div className="card">
          <h3>Export</h3>
          <button onClick={handleExport} disabled={isExporting}>
            {isExporting ? "Exporting..." : "Download Final Mix"}
          </button>
        </div>
      )}

      {project && <TrackList projectId={project.project_id} tracks={project.tracks} />}
    </div>
  );
}
