from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum


class GenerationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class GenerateRequest(BaseModel):
    prompt: str
    duration_seconds: Optional[float] = 10.0
    model_name: Optional[str] = "facebook/musicgen-small"
    project_id: Optional[str] = None


class GenerationJob(BaseModel):
    job_id: str
    status: GenerationStatus
    prompt: str
    model_name: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    output_path: Optional[str] = None
    error_message: Optional[str] = None
    duration_seconds: float


class Track(BaseModel):
    track_id: str
    name: str
    type: str  # "audio" or "midi"
    path: str
    muted: bool = False
    volume: float = 1.0
    pan: float = 0.0


class Note(BaseModel):
    pitch: int
    start: float
    end: float
    velocity: int
    instrument: int


class MidiUpdateRequest(BaseModel):
    notes: List[Note]
    tempo: Optional[int] = 120


class Project(BaseModel):
    project_id: str
    name: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    tracks: List[Track] = []
    generated_audio: Optional[str] = None
    midi_data: Optional[dict] = None
