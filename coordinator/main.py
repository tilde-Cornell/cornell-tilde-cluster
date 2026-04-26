"""
Cornell Tilde Cluster — Coordinator
=====================================
Accepts job submissions over HTTP and dispatches them to the Slurm cluster
running in Docker by invoking sbatch/squeue/scancel via `docker exec`.

Security model
--------------
No host directory is mounted into the compute node container. Job scripts are
piped directly into the slurmctld container as root-owned 600 files, then
deleted immediately after sbatch queues them (Slurm copies the script
internally). Output is retrieved from the compute container via `docker exec`
once the job finishes and stored in the coordinator's SQLite DB. The node
container therefore never sees any host filesystem path.

Run:
    cd coordinator
    pip install -r requirements.txt
    uvicorn main:app --host 0.0.0.0 --port 8000
"""

import json
import secrets
import subprocess
from typing import Optional

from fastapi import FastAPI, HTTPException, Request

import db

app = FastAPI(title="tilde@Cornell Cluster Coordinator", version="0.1.0")

CTRL  = "slurmctld"   # docker exec target for Slurm commands
NODE  = "node01"      # docker exec target for retrieving job output


def _exec(container: str, *cmd: str, stdin: Optional[str] = None) -> str:
    """Run a command inside a container. Raises RuntimeError on non-zero exit."""
    result = subprocess.run(
        ["docker", "exec", ("-i" if stdin is not None else ""), container, *cmd],
        input=stdin, capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


def _slurm(*cmd: str) -> str:
    return _exec(CTRL, *cmd)


@app.on_event("startup")
async def _startup() -> None:
    db.init_db()


# ── Job submission ─────────────────────────────────────────────────────────────

@app.post("/jobs", status_code=201)
async def submit_job(request: Request):
    body = await request.json()
    script: str       = body.get("script", "")
    input_data: dict  = body.get("input", {})
    submitted_by: str = body.get("submitted_by", "")
    cpus: int         = max(1, min(int(body.get("cpus", 1)), 4))
    mem_mb: int       = max(256, int(body.get("mem_mb", 512)))

    if not script:
        raise HTTPException(400, "script is required")

    job_id = secrets.token_hex(8)

    # Build the sbatch wrapper in memory — it never touches the host filesystem.
    # Output goes to /tmp inside the compute container, not a mounted host path.
    wrapper = f"""#!/bin/bash
#SBATCH --job-name={job_id}
#SBATCH --ntasks=1
#SBATCH --cpus-per-task={cpus}
#SBATCH --mem={mem_mb}M
#SBATCH --output=/tmp/{job_id}.out
#SBATCH --error=/tmp/{job_id}.out
export WORK_INPUT='{json.dumps(input_data)}'
python3 /tmp/{job_id}.py
"""

    try:
        # Write script and wrapper into the controller container as root (mode 600)
        # so no other process inside the container can read them.
        _exec(CTRL, "bash", "-c", f"cat > /tmp/{job_id}.py && chmod 600 /tmp/{job_id}.py",
              stdin=script)
        _exec(CTRL, "bash", "-c", f"cat > /tmp/{job_id}.sh && chmod 600 /tmp/{job_id}.sh",
              stdin=wrapper)

        # Submit. sbatch runs as root here; --uid runs the job as worker.
        # Phase 2: replace 'worker' with the submitting tilde user's UID.
        out = _slurm("sbatch", f"--uid=worker", f"/tmp/{job_id}.sh")
        slurm_job_id = out.split()[-1]

        # Script is now queued inside Slurm's spool — the temp file is no longer
        # needed and removing it closes the window where another process could read it.
        _exec(CTRL, "rm", "-f", f"/tmp/{job_id}.sh", f"/tmp/{job_id}.py")

    except RuntimeError as exc:
        _exec(CTRL, "rm", "-f", f"/tmp/{job_id}.sh", f"/tmp/{job_id}.py")
        raise HTTPException(500, f"sbatch failed: {exc}")

    db.save_job(job_id, slurm_job_id, submitted_by, cpus, mem_mb)
    return {"job_id": job_id, "slurm_job_id": slurm_job_id, "status": "queued"}


# ── Job status & output ────────────────────────────────────────────────────────

def _fetch_and_store_output(job: dict) -> str | None:
    """
    If the job is finished and we haven't retrieved output yet, pull it from
    /tmp inside the compute container and persist it to the DB. Then delete
    the temp file — it has no further use and shouldn't sit around.
    """
    if job.get("output") is not None:
        return job["output"]

    try:
        output = _exec(NODE, "cat", f"/tmp/{job['job_id']}.out")
        _exec(NODE, "rm", "-f", f"/tmp/{job['job_id']}.out")
        db.store_output(job["job_id"], output)
        return output
    except RuntimeError:
        return None


@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    try:
        job["slurm_state"] = _slurm(
            "squeue", "-j", job["slurm_job_id"], "-h", "-o", "%T"
        ) or "COMPLETED"
    except RuntimeError:
        job["slurm_state"] = "COMPLETED"

    terminal = job["slurm_state"] not in ("PENDING", "RUNNING")
    if terminal:
        job["output"] = _fetch_and_store_output(job)

    return job


@app.get("/jobs")
async def list_jobs():
    return db.list_jobs()


@app.delete("/jobs/{job_id}", status_code=200)
async def cancel_job(job_id: str):
    job = db.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    try:
        _slurm("scancel", job["slurm_job_id"])
    except RuntimeError as exc:
        raise HTTPException(500, f"scancel failed: {exc}")
    return {"ok": True}


# ── Cluster info ───────────────────────────────────────────────────────────────

@app.get("/nodes")
async def list_nodes():
    try:
        out = _slurm("sinfo", "-h", "-o", "%n %c %m %t %O")
    except RuntimeError as exc:
        raise HTTPException(500, str(exc))
    nodes = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5:
            nodes.append({
                "name":      parts[0],
                "cpus":      parts[1],
                "memory_mb": parts[2],
                "state":     parts[3],
                "cpu_load":  parts[4],
            })
    return nodes


@app.get("/queue")
async def queue():
    try:
        out = _slurm("squeue", "-h", "-o", "%i %j %u %t %M %C")
    except RuntimeError as exc:
        raise HTTPException(500, str(exc))
    jobs = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 6:
            jobs.append({
                "slurm_id": parts[0],
                "name":     parts[1],
                "user":     parts[2],
                "state":    parts[3],
                "time":     parts[4],
                "cpus":     parts[5],
            })
    return jobs
