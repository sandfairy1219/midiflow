export interface Track {
  track_id: string;
  name: string;
  type: "audio" | "midi";
  path: string;
  muted: boolean;
  volume: number;
  pan: number;
}

export interface GenerationJob {
  job_id: string;
  status: "pending" | "running" | "completed" | "failed";
  prompt: string;
  model_name: string;
  created_at: string;
  updated_at?: string;
  output_path?: string;
  error_message?: string;
  duration_seconds: number;
}

export interface Project {
  project_id: string;
  name: string;
  created_at: string;
  updated_at?: string;
  tracks: Track[];
  generated_audio?: string;
  midi_data?: { notes: Note[] };
}

export interface Note {
  pitch: number;
  start: number;
  end: number;
  velocity: number;
  instrument: number;
}
