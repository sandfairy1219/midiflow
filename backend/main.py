import asyncio
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks

from backend.schemas import GenerateRequest, GenerationJob, GenerationStatus, Project, Track, MidiUpdateRequest, RegenerateRequest
from fastapi.middleware.cors import CORSMiddleware

from backend.store import (
    create_project,
    get_project,
    create_job,
    get_job,
    update_job_status,
    ensure_project_dir,
)
from backend.pipelines.generate import generate_music, generate_from_melody
from backend.pipelines.analyze import analyze_audio
from backend.pipelines.midi_utils import notes_to_midi
from backend.pipelines.mix import mix_and_master


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Preload default model on startup
    from backend.pipelines.generate import get_model_and_processor
    print("Preloading MusicGen model...")
    get_model_and_processor("facebook/musicgen-small")
    print("Model loaded.")
    yield
    print("Shutting down.")


app = FastAPI(title="MidiFlow Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"status": "ok", "service": "midiflow-backend"}


@app.post("/projects", response_model=Project)
def create_new_project(name: Optional[str] = "New Project"):
    return create_project(name)


@app.get("/projects/{project_id}", response_model=Project)
def read_project(project_id: str):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@app.post("/projects/{project_id}/analyze", response_model=Project)
def analyze_project(project_id: str, background_tasks: BackgroundTasks):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.generated_audio or not os.path.exists(project.generated_audio):
        raise HTTPException(status_code=400, detail="No generated audio found for this project")

    background_tasks.add_task(_run_analysis, project_id, project.generated_audio)
    return project


async def _run_analysis(project_id: str, audio_path: str):
    try:
        pdir = ensure_project_dir(project_id)
        result = await asyncio.to_thread(analyze_audio, audio_path, pdir)

        project = get_project(project_id)
        if not project:
            return

        new_tracks = []
        for stem_name, stem_path in result["stems"].items():
            new_tracks.append(Track(
                track_id=f"{project_id}_stem_{stem_name}",
                name=stem_name.capitalize(),
                type="audio",
                path=stem_path,
            ))

        new_tracks.append(Track(
            track_id=f"{project_id}_midi_melody",
            name="Extracted Melody",
            type="midi",
            path=result["midi_path"],
        ))

        project.tracks = new_tracks
        project.midi_data = {"notes": result["notes"]}
        project.updated_at = datetime.now()
    except Exception as e:
        import traceback
        print(f"Analysis failed for {project_id}: {e}")
        traceback.print_exc()


@app.post("/generate", response_model=GenerationJob)
def generate_endpoint(request: GenerateRequest, background_tasks: BackgroundTasks):
    project_id = request.project_id or create_project("Generated Project").project_id
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    job = create_job(
        prompt=request.prompt,
        duration_seconds=request.duration_seconds or 10.0,
        model_name=request.model_name or "facebook/musicgen-small",
        project_id=project_id,
    )

    pdir = ensure_project_dir(project_id)
    output_filename = f"gen_{job.job_id}.wav"
    output_path = os.path.join(pdir, output_filename)

    background_tasks.add_task(_run_generation, job.job_id, request.prompt, output_path, request.duration_seconds or 10.0, request.model_name or "facebook/musicgen-small", project_id)
    return job


def _run_generation(job_id: str, prompt: str, output_path: str, duration: float, model_name: str, project_id: str):
    update_job_status(job_id, GenerationStatus.RUNNING)
    try:
        generate_music(prompt, output_path, duration, model_name)
        update_job_status(job_id, GenerationStatus.COMPLETED, output_path=output_path)

        project = get_project(project_id)
        if project:
            project.generated_audio = output_path
            project.updated_at = datetime.now()
    except Exception as e:
        update_job_status(job_id, GenerationStatus.FAILED, error_message=str(e))


@app.get("/jobs/{job_id}", response_model=GenerationJob)
def read_job(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/audio/{project_id}/{filename}")
def serve_audio(project_id: str, filename: str):
    pdir = ensure_project_dir(project_id)
    file_path = os.path.join(pdir, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    from fastapi.responses import FileResponse
    return FileResponse(file_path)


@app.post("/projects/{project_id}/midi", response_model=Project)
def update_midi(project_id: str, request: MidiUpdateRequest):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    pdir = ensure_project_dir(project_id)
    midi_path = os.path.join(pdir, "edited_melody.mid")
    notes_to_midi([n.model_dump() for n in request.notes], midi_path, request.tempo)

    # Update or add MIDI track
    existing = [t for t in project.tracks if t.track_id == f"{project_id}_midi_edited"]
    if existing:
        existing[0].path = midi_path
    else:
        project.tracks.append(Track(
            track_id=f"{project_id}_midi_edited",
            name="Edited Melody",
            type="midi",
            path=midi_path,
        ))

    project.midi_data = {"notes": [n.model_dump() for n in request.notes]}
    project.updated_at = datetime.now()
    return project


@app.post("/projects/{project_id}/regenerate", response_model=GenerationJob)
def regenerate_endpoint(project_id: str, request: RegenerateRequest, background_tasks: BackgroundTasks):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if not project.midi_data or not project.midi_data.get("notes"):
        raise HTTPException(status_code=400, detail="No MIDI notes available for regeneration")

    job = create_job(
        prompt=request.prompt,
        duration_seconds=request.duration_seconds or 10.0,
        model_name=request.model_name or "facebook/musicgen-small",
        project_id=project_id,
    )

    pdir = ensure_project_dir(project_id)
    output_filename = f"regen_{job.job_id}.wav"
    output_path = os.path.join(pdir, output_filename)

    background_tasks.add_task(
        _run_regeneration,
        job.job_id,
        request.prompt,
        project.midi_data["notes"],
        output_path,
        request.duration_seconds or 10.0,
        request.model_name or "facebook/musicgen-small",
        project_id,
    )
    return job


def _run_regeneration(job_id: str, prompt: str, notes: list, output_path: str, duration: float, model_name: str, project_id: str):
    update_job_status(job_id, GenerationStatus.RUNNING)
    try:
        generate_from_melody(prompt, notes, output_path, duration, model_name, is_notes=True)
        update_job_status(job_id, GenerationStatus.COMPLETED, output_path=output_path)

        project = get_project(project_id)
        if project:
            project.generated_audio = output_path
            project.updated_at = datetime.now()
    except Exception as e:
        import traceback
        update_job_status(job_id, GenerationStatus.FAILED, error_message=str(e))
        traceback.print_exc()


@app.post("/projects/{project_id}/export")
def export_project(project_id: str):
    project = get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    pdir = ensure_project_dir(project_id)
    output_path = os.path.join(pdir, "final_mix.wav")

    try:
        mix_and_master(project.tracks, output_path, fallback_audio_path=project.generated_audio)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    from fastapi.responses import FileResponse
    return FileResponse(output_path, filename="final_mix.wav", media_type="audio/wav")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
