#!/usr/bin/env python3
"""
tilde-compute — CLI for the tilde@Cornell cluster

Usage:
    python client.py submit script.py
    python client.py submit script.py --input '{"n": 42}' --cpus 2 --mem 1024
    python client.py status <job_id> [--watch]
    python client.py jobs
    python client.py nodes
    python client.py queue
    python client.py cancel <job_id>
"""

import argparse
import json
import sys
import time
from pathlib import Path

import requests

DEFAULT_URL = "http://localhost:8000" #TODO: Change to the dev server then the prod server


def _check(r: requests.Response) -> dict:
    try:
        r.raise_for_status()
    except requests.HTTPError:
        try:
            detail = r.json().get("detail", r.text)
        except Exception:
            detail = r.text
        print(f"Error {r.status_code}: {detail}")
        sys.exit(1)
    return r.json()


def cmd_submit(args, base: str) -> None:
    script = Path(args.script).read_text()
    payload = {
        "script":       script,
        "input":        json.loads(args.input) if args.input else {},
        "submitted_by": args.user or "",
        "cpus":         args.cpus,
        "mem_mb":       args.mem,
    }
    d = _check(requests.post(f"{base}/jobs", json=payload))
    print(f"Submitted  {d['job_id']}")
    print(f"Slurm ID   {d['slurm_job_id']}")


def cmd_status(args, base: str) -> None:
    while True:
        j = _check(requests.get(f"{base}/jobs/{args.job_id}"))
        print(f"\nJob        {j['job_id']}")
        print(f"Slurm ID   {j['slurm_job_id']}")
        print(f"State      {j.get('slurm_state', '—')}")
        print(f"CPUs       {j['cpus']}   Mem {j['mem_mb']} MB")
        print(f"Submitted  {j['submitted_at']}")
        if j.get("output"):
            print(f"\n─── output ───\n{j['output'].rstrip()}")
        state = j.get("slurm_state", "")
        if not args.watch or state not in ("PENDING", "RUNNING", "UNKNOWN", ""):
            break
        time.sleep(3)
        print("\n" + "─" * 44)


def cmd_jobs(args, base: str) -> None:
    rows = _check(requests.get(f"{base}/jobs"))
    if not rows:
        print("No jobs.")
        return
    print(f"{'JOB ID':<18}  {'SLURM':<8}  {'BY':<14}  {'CPUs':<5}  SUBMITTED")
    print("─" * 72)
    for j in rows:
        print(
            f"{j['job_id']:<18}  {j['slurm_job_id']:<8}  "
            f"{(j.get('submitted_by') or '—'):<14}  {j['cpus']:<5}  {j['submitted_at']}"
        )


def cmd_nodes(args, base: str) -> None:
    rows = _check(requests.get(f"{base}/nodes"))
    if not rows:
        print("No nodes registered.")
        return
    print(f"{'NAME':<12}  {'CPUs':<6}  {'MEM MB':<8}  {'STATE':<12}  CPU LOAD")
    print("─" * 54)
    for n in rows:
        print(
            f"{n['name']:<12}  {n['cpus']:<6}  {n['memory_mb']:<8}  "
            f"{n['state']:<12}  {n['cpu_load']}"
        )


def cmd_queue(args, base: str) -> None:
    rows = _check(requests.get(f"{base}/queue"))
    if not rows:
        print("Queue is empty.")
        return
    print(f"{'SLURM ID':<10}  {'NAME':<20}  {'USER':<10}  {'STATE':<10}  {'TIME':<8}  CPUs")
    print("─" * 72)
    for j in rows:
        print(
            f"{j['slurm_id']:<10}  {j['name']:<20}  {j['user']:<10}  "
            f"{j['state']:<10}  {j['time']:<8}  {j['cpus']}"
        )


def cmd_cancel(args, base: str) -> None:
    _check(requests.delete(f"{base}/jobs/{args.job_id}"))
    print(f"Cancelled {args.job_id}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="tilde-compute")
    parser.add_argument("--url", default=DEFAULT_URL, metavar="URL",
                        help=f"Coordinator URL (default: {DEFAULT_URL})")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("submit", help="Submit a Python script as a job")
    p.add_argument("script", help="Path to .py file")
    p.add_argument("--input", metavar="JSON",
                   help="Input data as JSON — available inside the script as $WORK_INPUT")
    p.add_argument("--user",  help="Your tilde username")
    p.add_argument("--cpus",  type=int, default=1, help="CPU cores to request (max 4)")
    p.add_argument("--mem",   type=int, default=512, metavar="MB", help="Memory in MB")

    p = sub.add_parser("status", help="Check job status and output")
    p.add_argument("job_id")
    p.add_argument("--watch", action="store_true", help="Poll until the job finishes")

    sub.add_parser("jobs",  help="List recent jobs")
    sub.add_parser("nodes", help="Show registered Slurm nodes")
    sub.add_parser("queue", help="Show the live Slurm queue")

    p = sub.add_parser("cancel", help="Cancel a running or pending job")
    p.add_argument("job_id")

    args = parser.parse_args()
    base = args.url.rstrip("/")

    try:
        {
            "submit": cmd_submit,
            "status": cmd_status,
            "jobs":   cmd_jobs,
            "nodes":  cmd_nodes,
            "queue":  cmd_queue,
            "cancel": cmd_cancel,
        }[args.cmd](args, base)
    except requests.ConnectionError:
        print(f"Cannot reach coordinator at {base} — is it running?")
        sys.exit(1)


if __name__ == "__main__":
    main()
