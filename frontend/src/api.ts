import type { Project, GenerationJob, Note } from "./types";

const API_BASE = "http://127.0.0.1:8000";

export async function createProject(name: string): Promise<Project> {
  const res = await fetch(`${API_BASE}/projects?name=${encodeURIComponent(name)}`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to create project");
  return res.json();
}

export async function getProject(projectId: string): Promise<Project> {
  const res = await fetch(`${API_BASE}/projects/${projectId}`);
  if (!res.ok) throw new Error("Failed to get project");
  return res.json();
}

export async function generateAudio(prompt: string, durationSeconds: number, projectId?: string): Promise<GenerationJob> {
  const res = await fetch(`${API_BASE}/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, duration_seconds: durationSeconds, project_id: projectId }),
  });
  if (!res.ok) throw new Error("Failed to start generation");
  return res.json();
}

export async function getJob(jobId: string): Promise<GenerationJob> {
  const res = await fetch(`${API_BASE}/jobs/${jobId}`);
  if (!res.ok) throw new Error("Failed to get job");
  return res.json();
}

export async function analyzeProject(projectId: string): Promise<Project> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/analyze`, { method: "POST" });
  if (!res.ok) throw new Error("Failed to start analysis");
  return res.json();
}

export async function saveMidi(projectId: string, notes: Note[], tempo: number = 120): Promise<Project> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/midi`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ notes, tempo }),
  });
  if (!res.ok) throw new Error("Failed to save MIDI");
  return res.json();
}

export async function regenerateAudio(projectId: string, prompt: string, durationSeconds: number): Promise<GenerationJob> {
  const res = await fetch(`${API_BASE}/projects/${projectId}/regenerate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, duration_seconds: durationSeconds }),
  });
  if (!res.ok) throw new Error("Failed to start regeneration");
  return res.json();
}

export function audioUrl(projectId: string, filename: string): string {
  return `${API_BASE}/audio/${projectId}/${filename}`;
}
