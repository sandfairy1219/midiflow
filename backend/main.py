import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware

from backend.schemas import GenerateRequest, GenerationJob, GenerationStatus, Project
from backend.store import (
    create_project,
    get_project,
    create_job,
    get_job,
    update_job_status,
    ensure_project_dir,
)
from backend.pipelines.generate import generate_music


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
