import os
import re
import uuid
from datetime import datetime
from typing import Dict, Optional

from backend.schemas import GenerationJob, GenerationStatus, Project


PROJECTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "projects")
os.makedirs(PROJECTS_DIR, exist_ok=True)

# In-memory stores (replace with DB later if needed)
jobs: Dict[str, GenerationJob] = {}
projects: Dict[str, Project] = {}


def sanitize_filename(name: str) -> str:
    return re.sub(r"[^\w\-_.]", "_", name).strip("_") or "untitled"


def create_project(name: str) -> Project:
    project_id = str(uuid.uuid4())[:8]
    project_dir = os.path.join(PROJECTS_DIR, project_id)
    os.makedirs(project_dir, exist_ok=True)
    project = Project(
        project_id=project_id,
        name=name,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    projects[project_id] = project
    return project


def get_project(project_id: str) -> Optional[Project]:
    return projects.get(project_id)


def create_job(prompt: str, duration_seconds: float, model_name: str, project_id: Optional[str] = None) -> GenerationJob:
    job_id = str(uuid.uuid4())[:8]
    job = GenerationJob(
        job_id=job_id,
        status=GenerationStatus.PENDING,
        prompt=prompt,
        model_name=model_name,
        created_at=datetime.now(),
        duration_seconds=duration_seconds,
    )
    jobs[job_id] = job
    return job


def get_job(job_id: str) -> Optional[GenerationJob]:
    return jobs.get(job_id)


def update_job_status(job_id: str, status: GenerationStatus, output_path: Optional[str] = None, error_message: Optional[str] = None):
    job = jobs.get(job_id)
    if job:
        job.status = status
        job.updated_at = datetime.now()
        if output_path is not None:
            job.output_path = output_path
        if error_message is not None:
            job.error_message = error_message


def project_dir(project_id: str) -> str:
    return os.path.join(PROJECTS_DIR, project_id)


def ensure_project_dir(project_id: str) -> str:
    pdir = project_dir(project_id)
    os.makedirs(pdir, exist_ok=True)
    return pdir
