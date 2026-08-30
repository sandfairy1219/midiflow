import os
import subprocess
import sys
import time
import requests


def wait_for_server(url="http://127.0.0.1:8000/", timeout=120):
    start = time.time()
    while time.time() - start < timeout:
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def main():
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.dirname(os.path.abspath(__file__))
    log_path = "test_analyze_server.log"
    log_file = open(log_path, "w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"],
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        print("Waiting for server...")
        if not wait_for_server():
            print("Server did not start")
            proc.terminate()
            log_file.close()
            print(open(log_path, encoding="utf-8").read()[-2000:])
            return 1

        # Create project
        r = requests.post("http://127.0.0.1:8000/projects", params={"name": "Analyze Test"}, timeout=5)
        project = r.json()
        project_id = project["project_id"]
        print("Created project:", project_id)

        # Use existing test audio if available, else generate
        test_audio = "test_output.wav"
        if not os.path.exists(test_audio):
            print("Generating test audio...")
            r = requests.post(
                "http://127.0.0.1:8000/generate",
                json={"prompt": "piano melody", "duration_seconds": 5.0, "project_id": project_id},
                timeout=10,
            )
            job = r.json()
            for _ in range(60):
                time.sleep(2)
                r = requests.get(f"http://127.0.0.1:8000/jobs/{job['job_id']}", timeout=5)
                if r.json()["status"] in ("completed", "failed"):
                    break
            test_audio = r.json().get("output_path", "")
        else:
            # Patch project generated_audio manually via store (or just place file in project dir)
            pdir = os.path.join("projects", project_id)
            os.makedirs(pdir, exist_ok=True)
            dest = os.path.join(pdir, "test_audio.wav")
            import shutil
            shutil.copy(test_audio, dest)
            # Update project via direct API not available; use generate endpoint instead for clean test
            # Instead, generate a new one anyway
            print("Generating fresh test audio...")
            r = requests.post(
                "http://127.0.0.1:8000/generate",
                json={"prompt": "piano melody", "duration_seconds": 5.0, "project_id": project_id},
                timeout=10,
            )
            job = r.json()
            for _ in range(60):
                time.sleep(2)
                r = requests.get(f"http://127.0.0.1:8000/jobs/{job['job_id']}", timeout=5)
                if r.json()["status"] in ("completed", "failed"):
                    break
            test_audio = r.json().get("output_path", "")

        print("Test audio:", test_audio)

        # Call analyze
        print("Starting analysis...")
        r = requests.post(f"http://127.0.0.1:8000/projects/{project_id}/analyze", timeout=10)
        print("Analyze response:", r.status_code, r.json().get("project_id"))

        # Poll project for tracks
        for i in range(120):
            time.sleep(3)
            try:
                r = requests.get(f"http://127.0.0.1:8000/projects/{project_id}", timeout=5)
            except Exception as e:
                print(f"Poll {i+1}: server not responding ({e})")
                continue
            project = r.json()
            tracks = project.get("tracks", [])
            print(f"Poll {i+1}: {len(tracks)} tracks")
            if len(tracks) >= 4:  # 4 stems + midi
                print("SUCCESS")
                print("Tracks:", [t["name"] for t in tracks])
                print("Notes count:", len(project.get("midi_data", {}).get("notes", [])))
                return 0

        print("Analysis did not complete in time")
        return 1
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        log_file.close()


if __name__ == "__main__":
    sys.exit(main())
