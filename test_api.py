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
    # Start server
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.dirname(os.path.abspath(__file__))
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    try:
        print("Waiting for server...")
        if not wait_for_server():
            print("Server did not start in time")
            out, _ = proc.communicate(timeout=5)
            print(out)
            return 1

        print("Server ready. Testing /generate...")
        r = requests.post(
            "http://127.0.0.1:8000/generate",
            json={"prompt": "lofi hip hop beat, piano and drums", "duration_seconds": 5.0},
            timeout=10,
        )
        print("Generate response:", r.status_code, r.json())
        job = r.json()
        job_id = job["job_id"]

        # Poll job status
        for _ in range(60):
            time.sleep(2)
            r = requests.get(f"http://127.0.0.1:8000/jobs/{job_id}", timeout=5)
            status = r.json()["status"]
            print(f"Job {job_id} status: {status}")
            if status in ("completed", "failed"):
                break

        job = r.json()
        if job["status"] == "completed":
            print("SUCCESS:", job["output_path"])
            assert os.path.exists(job["output_path"]), "Output file missing"
            print("Output file exists.")
        else:
            print("FAILED:", job.get("error_message"))
            return 1
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()

    return 0


if __name__ == "__main__":
    sys.exit(main())
