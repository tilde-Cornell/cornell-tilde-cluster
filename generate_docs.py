"""
Generates docs/cluster-guide.pdf
Run: python3 generate_docs.py
"""

from fpdf import FPDF
from fpdf.enums import XPos, YPos
import os

OUT_DIR  = os.path.join(os.path.dirname(__file__), "docs")
os.makedirs(OUT_DIR, exist_ok=True)
OUT_PATH = os.path.join(OUT_DIR, "cluster-guide.pdf")

# Palette
C_BLACK      = (15,  15,  15)
C_WHITE      = (255, 255, 255)
C_NAV        = (22,  35,  58)
C_SECTION_BG = (240, 244, 255)
C_CODE_BG    = (28,  28,  28)
C_CODE_FG    = (218, 218, 170)
C_RULE       = (100, 120, 180)
C_CAPTION    = (90,  90,  90)
C_ACCENT     = (55,  115, 210)

PAGE_W  = 210
PAGE_H  = 297
MARGIN  = 18
CONTENT = PAGE_W - 2 * MARGIN
FOOTER  = 18   # mm reserved at page bottom


class PDF(FPDF):
    def __init__(self):
        super().__init__()
        self.set_auto_page_break(auto=True, margin=FOOTER)
        self.set_margins(MARGIN, MARGIN, MARGIN)

    # ------------------------------------------------------------------
    # Primitives
    # ------------------------------------------------------------------

    def _y_remaining(self):
        return PAGE_H - self.get_y() - FOOTER

    def _ensure_space(self, mm):
        """Add a new page if fewer than `mm` millimetres remain."""
        if self._y_remaining() < mm:
            self.add_page()

    def _section_break(self, min_remaining=90):
        """
        Break to a new page only when we're low on space.
        If there's plenty of room left, just add a gap.
        """
        if self._y_remaining() < min_remaining:
            self.add_page()
        else:
            self.ln(10)

    # ------------------------------------------------------------------
    # Header / footer (skip on cover)
    # ------------------------------------------------------------------

    def header(self):
        if self.page_no() == 1:
            return
        self.set_fill_color(*C_NAV)
        self.rect(0, 0, PAGE_W, 10, "F")
        self.set_font("Helvetica", "B", 8)
        self.set_text_color(*C_WHITE)
        self.set_xy(MARGIN, 1.8)
        self.cell(0, 6, "tilde@Cornell Cluster -- Developer Guide", align="L")
        self.set_xy(-MARGIN - 20, 1.8)
        self.cell(20, 6, f"p. {self.page_no()}", align="R")
        self.set_text_color(*C_BLACK)
        # Reset cursor to the top margin so content never draws on top of the
        # header bar, regardless of where the last cell() left the Y position.
        self.set_y(MARGIN)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-14)
        self.set_draw_color(*C_RULE)
        self.set_line_width(0.3)
        self.line(MARGIN, self.get_y(), PAGE_W - MARGIN, self.get_y())
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*C_CAPTION)
        self.cell(0, 8, "tilde@Cornell -- internal documentation", align="C")
        self.set_text_color(*C_BLACK)

    # ------------------------------------------------------------------
    # Cover
    # ------------------------------------------------------------------

    def cover(self):
        self.add_page()
        self.set_fill_color(*C_NAV)
        self.rect(0, 0, PAGE_W, 85, "F")
        self.set_font("Helvetica", "B", 28)
        self.set_text_color(*C_WHITE)
        self.set_xy(MARGIN, 22)
        self.cell(CONTENT, 14, "tilde@Cornell Cluster", align="C",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Helvetica", "", 15)
        self.set_x(MARGIN)
        self.cell(CONTENT, 10, "Developer Guide", align="C",
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Helvetica", "", 9)
        self.set_x(MARGIN)
        self.cell(CONTENT, 8,
                  "Testing  *  Architecture  *  Line-by-Line Code Reference",
                  align="C")
        self.set_text_color(*C_BLACK)
        self.set_xy(MARGIN, 96)

    # ------------------------------------------------------------------
    # Section heading  (accent bar + title + rule)
    # ------------------------------------------------------------------

    def section(self, title):
        self.ln(2)
        self.set_fill_color(*C_ACCENT)
        self.rect(MARGIN, self.get_y(), 2.5, 9, "F")
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*C_NAV)
        self.set_x(MARGIN + 5)
        self.cell(CONTENT - 5, 9, title,
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*C_RULE)
        self.set_line_width(0.3)
        self.line(MARGIN, self.get_y(), PAGE_W - MARGIN, self.get_y())
        self.set_text_color(*C_BLACK)
        self.ln(4)

    # ------------------------------------------------------------------
    # Sub-heading
    # ------------------------------------------------------------------

    def sub(self, title):
        self._ensure_space(28)
        self.ln(3)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*C_ACCENT)
        self.set_x(MARGIN)
        self.cell(CONTENT, 6, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*C_BLACK)
        self.ln(1)

    # ------------------------------------------------------------------
    # Body paragraph
    # ------------------------------------------------------------------

    def body(self, text):
        self.set_font("Helvetica", "", 9.5)
        self.set_text_color(*C_BLACK)
        self.set_x(MARGIN)
        self.multi_cell(CONTENT, 5.5, text,
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)

    # ------------------------------------------------------------------
    # Code block  -- THE KEY FIX:
    # Measure the full block height before drawing anything.
    # If it won't fit on the current page, break first.
    # ------------------------------------------------------------------

    def code(self, text, caption=""):
        lines   = text.strip().split("\n")
        line_h  = 4.8
        pad     = 4
        block_h = len(lines) * line_h + pad * 2
        cap_h   = 5 if caption else 0
        total_h = block_h + cap_h + 4   # +4 for trailing ln

        # If the block won't fit, move to a fresh page before drawing.
        # Exception: if the block itself is taller than one usable page
        # we have no choice but to let it flow (very long blocks only).
        usable = PAGE_H - MARGIN - FOOTER - 12   # 12 for header
        if total_h <= usable:
            self._ensure_space(total_h)

        top = self.get_y()

        # Background rect
        self.set_fill_color(*C_CODE_BG)
        self.rect(MARGIN, top, CONTENT, block_h, "F")

        # Code text
        self.set_font("Courier", "", 8)
        self.set_text_color(*C_CODE_FG)
        self.set_xy(MARGIN + pad, top + pad)

        for line in lines:
            if len(line) > 93:
                line = line[:92] + "..."
            self.set_x(MARGIN + pad)
            self.cell(CONTENT - pad * 2, line_h, line,
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        # Move cursor below the rect (not relying on cell positioning)
        self.set_y(top + block_h)
        self.set_text_color(*C_BLACK)

        if caption:
            self.set_font("Helvetica", "I", 7.5)
            self.set_text_color(*C_CAPTION)
            self.set_x(MARGIN)
            self.cell(CONTENT, cap_h, caption,
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_text_color(*C_BLACK)
        self.ln(3)

    # ------------------------------------------------------------------
    # Bullet list
    # ------------------------------------------------------------------

    def bullets(self, items):
        for item in items:
            self._ensure_space(12)
            self.set_font("Helvetica", "B", 10)
            self.set_text_color(*C_ACCENT)
            self.set_x(MARGIN + 2)
            self.cell(5, 5.5, "-")
            self.set_font("Helvetica", "", 9.5)
            self.set_text_color(*C_BLACK)
            self.set_x(MARGIN + 7)
            self.multi_cell(CONTENT - 7, 5.5, item,
                            new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    # ------------------------------------------------------------------
    # TOC entry
    # ------------------------------------------------------------------

    def toc_entry(self, num, title, desc):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(*C_ACCENT)
        self.set_x(MARGIN)
        self.cell(12, 7, num)
        self.set_text_color(*C_BLACK)
        self.cell(CONTENT - 12, 7, title,
                  new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(*C_CAPTION)
        self.set_x(MARGIN + 12)
        self.multi_cell(CONTENT - 12, 5, desc,
                        new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*C_BLACK)
        self.ln(1)


# ======================================================================
# Document
# ======================================================================

pdf = PDF()

# ── Cover ─────────────────────────────────────────────────────────────
pdf.cover()

pdf.set_font("Helvetica", "", 9.5)
pdf.body(
    "This document covers everything you need to understand, test, and extend the "
    "tilde@Cornell compute cluster. Part one is a step-by-step testing guide for "
    "verifying a working installation. Part two is a complete line-by-line explanation "
    "of every file in the codebase."
)

pdf.section("Contents")
pdf.toc_entry("1",  "System Overview",
              "How the pieces fit together at a high level.")
pdf.toc_entry("2",  "Testing Guide",
              "Step-by-step verification from Docker startup through job output.")
pdf.toc_entry("3",  "Dockerfile",
              "Building a single image that serves as both controller and compute node.")
pdf.toc_entry("4",  "docker-compose.yml",
              "Service definitions, resource limits, and named volumes.")
pdf.toc_entry("5",  "slurm.conf",
              "Every configuration directive and why it is set the way it is.")
pdf.toc_entry("6",  "controller.sh",
              "Munge key generation, daemon startup, and the gosu drop.")
pdf.toc_entry("7",  "node.sh",
              "Readiness polling, CPU affinity, and slurmd registration.")
pdf.toc_entry("8",  "coordinator/db.py",
              "SQLite schema, WAL mode, and the output caching pattern.")
pdf.toc_entry("9",  "coordinator/main.py",
              "Script piping, sbatch submission, and secure output retrieval.")
pdf.toc_entry("10", "coordinator/client.py",
              "CLI argument parsing, polling loop, and error handling.")
pdf.toc_entry("11", "tilde-node",
              "Lifecycle management, drain-before-stop, and the readiness timeout.")

# ======================================================================
# 1. SYSTEM OVERVIEW
# ======================================================================
pdf.add_page()
pdf.section("1  System Overview")

pdf.body(
    "The cluster runs entirely inside Docker on your Mac. Docker Desktop provides "
    "a Linux VM (LinuxKit) that gives real Linux kernel features -- cgroups, "
    "namespaces, CPU quotas -- that are not available on macOS natively. Slurm, "
    "which is Linux-only, runs inside two containers built from the same image."
)

pdf.sub("The three processes you run")
pdf.bullets([
    "./tilde-node start -- builds Docker images, starts slurmctld + slurmd, waits "
    "for Slurm to be ready, then exits. The containers keep running in the background.",
    "uvicorn main:app -- the coordinator HTTP API. Runs on your Mac (not in Docker). "
    "Accepts job submissions, calls docker exec to talk to Slurm, stores results in SQLite.",
    "python client.py -- the CLI users call to submit scripts, check status, and get output.",
])

pdf.sub("Data flow for a single job")
pdf.bullets([
    "1. User runs:  python client.py submit myscript.py --cpus 2",
    "2. client.py POSTs the script text and options to the coordinator at POST /jobs.",
    "3. Coordinator generates a job_id, builds an sbatch wrapper in memory, pipes "
    "both files into the slurmctld container via docker exec -i. Nothing touches the host filesystem.",
    "4. Coordinator calls sbatch inside slurmctld. Slurm assigns a numeric ID and queues "
    "the job. Temp files in /tmp are deleted immediately after sbatch reads them.",
    "5. slurmctld dispatches the job to slurmd (node01). slurmd pins the job to the "
    "requested CPU cores via sched_setaffinity(), then runs the Python script as worker.",
    "6. Output is written to /tmp/{job_id}.out inside the node01 container.",
    "7. When the user checks status, coordinator calls squeue to get state. Once finished, "
    "it runs docker exec node01 cat /tmp/{job_id}.out, stores output in SQLite, deletes "
    "the temp file, and returns the output in the HTTP response.",
])

pdf.sub("Security boundaries")
pdf.bullets([
    "Host filesystem: nothing is bind-mounted into the compute container. "
    "A job cannot see any path on your Mac.",
    "CPU: Docker's cpus: 4.0 limits the container to 4 CPU shares at the kernel level. "
    "Slurm's task/affinity further pins each job to its allocated cores only.",
    "Memory: Docker's mem_limit: 4g enforced by the host kernel. A runaway job is "
    "OOM-killed before it can consume more than 4 GB.",
    "Privilege escalation: security_opt no-new-privileges:true blocks SUID binaries "
    "inside the container from gaining capabilities.",
    "Container escape: no privileged:true means root inside the container cannot "
    "access host devices, mount host filesystems, or break out of namespaces.",
])

# ======================================================================
# 2. TESTING GUIDE
# ======================================================================
pdf._section_break()
pdf.section("2  Testing Guide")

pdf.sub("Prerequisites")
pdf.code(
    "docker info                    # Docker Desktop must be running\n"
    "python3 --version              # need 3.10+\n"
    "cd cornell-tilde-cluster/coordinator\n"
    "pip install -r requirements.txt"
)

pdf.sub("Step 1 -- Build and start the cluster")
pdf.code("./tilde-node start",
         "Takes ~2 minutes on first run (downloads Ubuntu, installs Slurm).")
pdf.body(
    "Expected final output: sinfo shows PARTITION=tilde, STATE=idle, NODES=1, NODELIST=node01. "
    "If STATE=down, run ./tilde-node logs to investigate -- most likely slurmd raced "
    "ahead of slurmctld on startup."
)

pdf.sub("Step 2 -- Verify Slurm internals directly")
pdf.code(
    "# Confirm slurmctld is reachable\n"
    "docker exec slurmctld scontrol ping\n"
    "# Expected: Slurmctld(primary) at slurmctld is UP\n"
    "\n"
    "# Confirm node reports 4 CPUs\n"
    "docker exec slurmctld sinfo -l\n"
    "# CPUS column = 4, STATE = idle\n"
    "\n"
    "# Verify munge auth works end-to-end\n"
    "docker exec slurmctld munge -n | docker exec -i slurmctld unmunge\n"
    "# Expected: STATUS: Success (0)\n"
    "\n"
    "# Confirm worker user exists in compute container\n"
    "docker exec node01 id worker\n"
    "# Expected: uid=1001(worker) gid=1001(worker)"
)

pdf.sub("Step 3 -- Start the coordinator")
pdf.code(
    "# In a second terminal:\n"
    "cd coordinator\n"
    "uvicorn main:app --host 0.0.0.0 --port 8000\n"
    "\n"
    "# Verify in a third terminal:\n"
    "curl http://localhost:8000/nodes\n"
    '# Expected: [{"name":"node01","cpus":"4","state":"idle",...}]'
)

pdf.sub("Step 4 -- Submit a minimal job")
pdf.code(
    "# Create test script at /tmp/hello.py:\n"
    "# import os, platform\n"
    "# print('hostname:', platform.node())\n"
    "# print('cpu count:', os.cpu_count())\n"
    "# print('WORK_INPUT:', os.environ.get('WORK_INPUT', 'none'))\n"
    "\n"
    "# Submit\n"
    "python coordinator/client.py submit /tmp/hello.py --user testuser\n"
    "\n"
    "# Watch until complete\n"
    "python coordinator/client.py status <job_id> --watch"
)

pdf.sub("Step 5 -- Verify CPU pinning")
pdf.code(
    "# cpu_burn.py: burns CPU for 10 seconds\n"
    "# import time\n"
    "# end = time.time() + 10\n"
    "# while time.time() < end: pass\n"
    "# print('done')\n"
    "\n"
    "# Submit requesting 2 cores\n"
    "python coordinator/client.py submit /tmp/cpu_burn.py --cpus 2\n"
    "\n"
    "# While it runs, in another terminal:\n"
    "docker exec slurmctld squeue\n"
    "# CPUS column must show 2, not 4"
)

pdf.sub("Step 6 -- Test queue depth")
pdf.code(
    "# 3 jobs each requesting 2 CPUs; node has 4 total\n"
    "for i in 1 2 3; do\n"
    "  python coordinator/client.py submit /tmp/cpu_burn.py --cpus 2\n"
    "done\n"
    "\n"
    "docker exec slurmctld squeue\n"
    "# Two jobs: RUNNING (R)    One job: PENDING (PD)"
)

pdf.sub("Step 7 -- Test cancellation")
pdf.code(
    "python coordinator/client.py cancel <job_id>\n"
    "docker exec slurmctld squeue   # job should be gone"
)

pdf.sub("Step 8 -- Verify the host filesystem boundary")
pdf.code(
    "# escape_test.py\n"
    "# import os, subprocess\n"
    "# r = subprocess.run(['ls', '/Users'], capture_output=True, text=True)\n"
    "# print('Users dir:', r.stdout or 'NOT VISIBLE')\n"
    "# print('/ contents:', os.listdir('/'))\n"
    "\n"
    "python coordinator/client.py submit /tmp/escape_test.py --watch\n"
    "# /Users must NOT appear. / shows only Linux container paths."
)

pdf.sub("Step 9 -- Test input data passing")
pdf.code(
    "# input_test.py\n"
    "# import os, json\n"
    "# data = json.loads(os.environ['WORK_INPUT'])\n"
    "# print('x * y =', data['x'] * data['y'])\n"
    "\n"
    'python coordinator/client.py submit /tmp/input_test.py \\\n'
    '  --input \'{"x": 6, "y": 7}\' --watch\n'
    "# output: x * y = 42"
)

pdf.sub("Step 10 -- Stop cleanly")
pdf.code("./tilde-node stop   # drains in-flight jobs then removes containers")

# ======================================================================
# 3. DOCKERFILE
# ======================================================================
pdf._section_break()
pdf.section("3  slurm/docker/Dockerfile")

pdf.code(
    "FROM ubuntu:22.04\n"
    "ENV DEBIAN_FRONTEND=noninteractive"
)
pdf.body(
    "Ubuntu 22.04 ships Slurm 21.08 in its package repos -- stable and well-tested. "
    "DEBIAN_FRONTEND=noninteractive tells apt never to open interactive dialogs "
    "(timezone prompts, keyboard layout questions). Without it some installs hang "
    "inside a Docker build waiting for input that can never arrive."
)

pdf.code(
    "RUN apt-get update && apt-get install -y --no-install-recommends \\\n"
    "    slurmctld slurmd slurm-client munge python3 python3-pip gosu curl \\\n"
    "    && rm -rf /var/lib/apt/lists/*"
)
pdf.bullets([
    "slurmctld -- the central controller daemon. Manages the job queue, "
    "scheduling decisions, and node state.",
    "slurmd -- the compute daemon. Receives dispatched jobs from slurmctld "
    "and runs them as child processes.",
    "slurm-client -- CLI tools: sbatch (submit), squeue (list), scontrol (admin), "
    "scancel (cancel), sinfo (node info). Both containers need these because the "
    "coordinator calls them via docker exec.",
    "munge -- the shared-secret authentication library. Every message between "
    "slurmctld and slurmd is signed with a munge credential. Without a matching "
    "key all requests are rejected.",
    "python3, python3-pip -- jobs are Python scripts; the compute node needs Python.",
    "gosu -- a minimal su replacement designed for containers. Unlike standard su, "
    "it does a clean exec (replaces the shell process) so no zombie parent process "
    "is left behind.",
    "--no-install-recommends -- skips optional packages, keeping the image smaller.",
    "rm -rf /var/lib/apt/lists/* -- deletes the package index downloaded by "
    "apt-get update. Only needed during the build. Saves ~50 MB from the final image.",
])

pdf.code(
    "RUN mkdir -p /var/spool/slurmctld /var/spool/slurmd /var/run/slurm /var/log/slurm\n"
    "    && chown slurm:slurm /var/spool/slurmctld /var/spool/slurmd "
    "/var/run/slurm /var/log/slurm"
)
pdf.body(
    "Creates directories Slurm's config points at (StateSaveLocation, SlurmdSpoolDir, "
    "pid files, logs) and gives ownership to the slurm system user -- which the packages "
    "created during install. Required because slurmctld runs as the slurm user (via gosu), "
    "not root."
)

pdf.code(
    "RUN useradd -m -s /bin/bash worker\n"
    "COPY entrypoints/ /entrypoints/\n"
    "RUN chmod +x /entrypoints/*.sh"
)
pdf.body(
    "useradd -m creates the worker user with a home directory. All job processes run "
    "as this unprivileged user. -s /bin/bash sets the login shell. chmod +x makes both "
    "entrypoint scripts executable. The same image serves as both the controller and the "
    "compute node -- the entrypoint specified in docker-compose.yml decides the role."
)

# ======================================================================
# 4. DOCKER-COMPOSE.YML
# ======================================================================
pdf._section_break()
pdf.section("4  slurm/docker-compose.yml")

pdf.code(
    "x-slurm-base: &slurm-base\n"
    "  build:\n"
    "    context: ./docker\n"
    "  restart: unless-stopped\n"
    "  networks:\n"
    "    - slurm-net"
)
pdf.body(
    "A YAML anchor -- a reusable block. The x- prefix marks it as an extension key "
    "that Docker Compose ignores. &slurm-base names it. Services merge it in with "
    "<<: *slurm-base. restart: unless-stopped is the crash-recovery heartbeat at the "
    "container level: Docker restarts the container automatically if it crashes, unless "
    "you explicitly ran docker compose down. slurm-net puts both containers on the same "
    "virtual bridge network so they resolve each other by hostname."
)

pdf.code(
    "  slurmctld:\n"
    "    container_name: slurmctld\n"
    "    hostname: slurmctld"
)
pdf.body(
    "container_name is what docker exec uses to find the container. hostname is what "
    "the container reports as its own hostname -- this must match SlurmctldHost=slurmctld "
    "in slurm.conf, because that is how slurmd knows which machine to register with and "
    "send heartbeats to. Docker's internal DNS on slurm-net resolves container hostnames "
    "to their IPs automatically."
)

pdf.code(
    "    volumes:\n"
    "      - ./conf:/etc/slurm:ro       # Slurm config, read-only\n"
    "      - slurm-state:/var/spool/slurmctld  # job queue persists across restarts\n"
    "      - munge-key:/etc/munge       # shared secret between controller and node\n"
    "      - slurm-log:/var/log/slurm   # logs persist across restarts"
)
pdf.body(
    "The :ro flag on ./conf makes slurm.conf read-only inside the container so a "
    "compromised container cannot alter cluster configuration. slurm-state is a Docker "
    "named volume (not a host path) where slurmctld persists the job queue, so queued "
    "jobs survive container restarts. munge-key is a named volume shared between both "
    "containers so they use the same munge secret. slurm-log persists logs for debugging."
)

pdf.code(
    "  node01:\n"
    "    cpus: 4.0\n"
    "    mem_limit: 4g\n"
    "    security_opt:\n"
    "      - no-new-privileges:true"
)
pdf.bullets([
    "cpus: 4.0 -- Docker creates a Linux cgroup in the VM limiting this container to "
    "4 CPU shares. Enforced by the host kernel entirely outside the container.",
    "mem_limit: 4g -- a cgroup memory limit of 4 GB for the entire container. If total "
    "memory crosses 4 GB, the kernel OOM-kills the heaviest process. Enforced at the "
    "Docker VM layer without requiring privileged mode inside the container.",
    "no-new-privileges:true -- sets PR_SET_NO_NEW_PRIVS on the root process, inherited "
    "by all children. Prevents any process from gaining capabilities via SUID binaries.",
    "No host bind mounts on node01 -- the compute container mounts no host directory. "
    "A job cannot see any path on your Mac. Scripts arrive via Slurm's internal spool; "
    "output is retrieved via docker exec after completion.",
])

pdf.code(
    "volumes:\n"
    "  slurm-state:\n"
    "  slurm-spool:\n"
    "  munge-key:\n"
    "  slurm-log:"
)
pdf.body(
    "Declaring names at the top level tells Docker Compose to create and manage these "
    "as Docker-native volumes stored in Docker's own storage area, not in your home "
    "directory. They persist across docker compose down and are only removed with "
    "docker compose down -v."
)

# ======================================================================
# 5. SLURM.CONF
# ======================================================================
pdf._section_break()
pdf.section("5  slurm/conf/slurm.conf")

entries = [
    ("ClusterName=tildecluster",
     "A name for this cluster used in accounting logs and state files. Arbitrary string."),
    ("SlurmctldHost=slurmctld",
     "The hostname of the slurmctld machine. Every slurmd uses this to know where to "
     "register and send heartbeats. Must match the container's hostname in "
     "docker-compose.yml so Docker's internal DNS can resolve it."),
    ("AuthType=auth/munge  /  CryptoType=crypto/munge",
     "Both tell Slurm to use munge for all inter-daemon authentication. Every message "
     "between slurmctld and slurmd is wrapped in a munge credential signed with the "
     "shared key. Without a matching key all requests are rejected."),
    ("SlurmUser=slurm",
     "The Linux user slurmctld runs as. The gosu slurm in controller.sh drops to this "
     "user. slurmd itself runs as root because it needs to set CPU affinity and manage "
     "job processes."),
    ("SlurmctldPort=6817  /  SlurmdPort=6818",
     "TCP ports the daemons listen on. 6817/6818 are Slurm's IANA-registered ports. "
     "slurmd connects to slurmctld on 6817; slurmctld dispatches jobs to slurmd on 6818."),
    ("StateSaveLocation=/var/spool/slurmctld",
     "Where slurmctld persists the entire job queue to disk. If slurmctld restarts, it "
     "reads this directory and recovers all queued and running jobs."),
    ("SlurmdSpoolDir=/var/spool/slurmd",
     "Where slurmd stores scripts dispatched to it by slurmctld. This is where your job "
     "script lives during execution -- Slurm copies it here internally when sbatch is called."),
    ("ProctrackType=proctrack/linuxproc",
     "How slurmd tracks which OS processes belong to a job. linuxproc scans the process "
     "tree via /proc to find all descendants of the job's initial process. Does not "
     "require privileged mode or cgroup filesystem access."),
    ("ReturnToService=1",
     "When a node goes DOWN (e.g., slurmd restarts), automatically brings it back to "
     "IDLE once slurmd reconnects and passes health checks. Without this you would have "
     "to run scontrol update NodeName=node01 State=RESUME manually every time."),
    ("SchedulerType=sched/backfill",
     "Slurm's default and most widely used scheduler. Tries the highest-priority job "
     "first. If it cannot start immediately, looks ahead to find when it could start, "
     "then backfills lower-priority jobs into the gap -- maximising utilisation without "
     "delaying higher-priority work."),
    ("SelectType=select/cons_tres  /  SelectTypeParameters=CR_Core_Memory",
     "cons_tres = consumable trackable resources. Slurm tracks individual CPUs and memory "
     "as discrete resources consumed by jobs. CR_Core_Memory means: allocate at the level "
     "of individual cores (not whole sockets) and also track memory. Enables "
     "--cpus-per-task=2 to give a job exactly 2 specific cores."),
    ("TaskPlugin=task/affinity",
     "After Slurm assigns specific cores to a job, task/affinity calls sched_setaffinity() "
     "on the job process to pin it to those cores. sched_setaffinity is a Linux kernel "
     "call that sets a CPU affinity bitmask. slurmd (running as root) has permission to "
     "set this on worker processes it spawns. No cgroup filesystem access required."),
    ("AccountingStorageType=accounting_storage/none",
     "Disables the accounting subsystem for Phase 1. Phase 2 changes this to "
     "accounting_storage/slurmdbd and adds the slurmdbd service + MySQL to Docker Compose "
     "to enable fairshare scheduling (the 2x compute model)."),
    ("NodeName=node01 CPUs=4 RealMemory=4096 ...",
     "Static description of your compute node. node01 must match the container's hostname. "
     "CPUs=4 is what Slurm advertises. RealMemory=4096 MB must be <= mem_limit in "
     "docker-compose.yml. Sockets=1 CoresPerSocket=4 ThreadsPerCore=1 describes the "
     "topology (1 socket, 4 real cores, no hyperthreading). State=UNKNOWN means let "
     "slurmd report the actual state when it connects."),
    ("PartitionName=tilde ...",
     "A partition is Slurm's term for a queue. Default=YES means jobs go here if no "
     "--partition is specified. MaxTime=08:00:00 hard-kills any job running longer than "
     "8 hours."),
]
for key, explanation in entries:
    pdf.sub(key)
    pdf.body(explanation)

# ======================================================================
# 6. CONTROLLER.SH
# ======================================================================
pdf._section_break()
pdf.section("6  slurm/docker/entrypoints/controller.sh")

pdf.code("#!/bin/bash\nset -eu")
pdf.body(
    "-e exits immediately on any command returning non-zero. "
    "-u treats unset variables as errors. Together they make the script fail loudly "
    "and early rather than silently continuing in a broken state."
)

pdf.code(
    "if [ ! -s /etc/munge/munge.key ]; then\n"
    "    dd if=/dev/urandom bs=1 count=1024 > /etc/munge/munge.key 2>/dev/null\n"
    "fi"
)
pdf.body(
    "-s tests that the file exists AND is non-empty. dd if=/dev/urandom reads from "
    "the kernel's cryptographically secure random source. bs=1 count=1024 reads 1024 "
    "bytes. 2>/dev/null suppresses dd's progress output. Runs only once -- on "
    "subsequent container starts the key already exists on the munge-key named volume."
)

pdf.code(
    "chown munge:munge /etc/munge/munge.key\n"
    "chmod 400 /etc/munge/munge.key\n"
    "runuser -u munge -- munged\n"
    "sleep 2"
)
pdf.body(
    "chown munge:munge makes the key owned by the munge system user. "
    "chmod 400 = owner can read, nobody else can read or write. munged daemonizes itself, "
    "reads the key, and starts accepting signing/verification requests on a Unix socket. "
    "sleep 2 gives munged time to be ready before slurmctld tries to use it."
)

pdf.code("exec gosu slurm slurmctld -D -v")
pdf.body(
    "exec replaces the current shell process with slurmctld -- no shell stays alive "
    "as a parent, which avoids zombie processes. gosu slurm drops from root to the slurm "
    "user. -D runs in foreground so Docker can see stdout/stderr via docker logs. "
    "-v enables verbose logging."
)

# ======================================================================
# 7. NODE.SH
# ======================================================================
pdf._section_break()
pdf.section("7  slurm/docker/entrypoints/node.sh")

pdf.code("until [ -s /etc/munge/munge.key ]; do sleep 1; done")
pdf.body(
    "Polls until the munge key file exists and is non-empty on the shared munge-key "
    "volume. The controller generates this file on startup. -s (non-empty) guards against "
    "a race where the file is created but not yet written. The node cannot start munged "
    "without this key, so this loop is the synchronisation point between the two containers."
)

pdf.code(
    "until scontrol ping 2>/dev/null | grep -q 'UP\\|is UP'; do sleep 3; done"
)
pdf.body(
    "scontrol ping sends a test message to slurmctld and prints whether it is reachable. "
    "grep -q checks for the UP string without printing it. 2>/dev/null suppresses errors "
    "during the retry window when slurmctld is not ready yet. Polls every 3 seconds. "
    "Prevents slurmd from trying to register before slurmctld is ready, which would "
    "cause slurmd to mark itself DOWN."
)

pdf.code("exec slurmd -D -N node01 -v")
pdf.body(
    "-N node01 explicitly tells slurmd its own node name -- must match NodeName= in "
    "slurm.conf. slurmd registers with slurmctld using this name. Runs as root (no gosu) "
    "because it needs to call sched_setaffinity() on job processes, read root-owned "
    "scripts in /tmp, and send SIGKILL to runaway jobs."
)

# ======================================================================
# 8. COORDINATOR/DB.PY
# ======================================================================
pdf._section_break()
pdf.section("8  coordinator/db.py")

pdf.code("DB_PATH = Path(__file__).parent / 'coordinator.sqlite3'")
pdf.body(
    "Path(__file__) is the absolute path of db.py itself. .parent is the directory "
    "containing it (coordinator/). The SQLite file lives alongside the code, not in "
    "/tmp or a hardcoded path, so it persists between coordinator restarts."
)

pdf.code(
    "def _conn() -> sqlite3.Connection:\n"
    "    conn = sqlite3.connect(DB_PATH)\n"
    "    conn.row_factory = sqlite3.Row\n"
    "    conn.execute('PRAGMA journal_mode=WAL')\n"
    "    return conn"
)
pdf.bullets([
    "sqlite3.connect -- opens or creates the database file.",
    "row_factory = sqlite3.Row -- query results become Row objects where columns are "
    "accessible by name (row['job_id']) instead of index (row[0]).",
    "PRAGMA journal_mode=WAL -- Write-Ahead Logging. The default mode locks the entire "
    "database for every write. WAL allows reads to proceed concurrently with a write -- "
    "important because the coordinator handles simultaneous HTTP requests.",
])

pdf.code(
    "CREATE TABLE IF NOT EXISTS jobs (\n"
    "    job_id        TEXT PRIMARY KEY,\n"
    "    slurm_job_id  TEXT,\n"
    "    submitted_by  TEXT NOT NULL DEFAULT '',\n"
    "    submitted_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,\n"
    "    cpus          INTEGER NOT NULL DEFAULT 1,\n"
    "    mem_mb        INTEGER NOT NULL DEFAULT 512,\n"
    "    output        TEXT\n"
    ")"
)
pdf.bullets([
    "job_id -- our internal identifier, a 16-character hex string from secrets.token_hex(8).",
    "slurm_job_id -- the integer Slurm assigns (1, 2, 3...) returned by sbatch. "
    "We need both: our API uses job_id, but squeue/scancel require the Slurm integer.",
    "submitted_at -- DEFAULT CURRENT_TIMESTAMP means SQLite fills this automatically on insert.",
    "output -- TEXT in SQLite stores arbitrarily large strings. Initially NULL. "
    "Set once by store_output() after the job finishes. Once set, the coordinator never "
    "re-reads from the container for this job.",
])

pdf.code(
    "conn.execute(\n"
    "    'INSERT INTO jobs (...) VALUES (?,?,?,?,?)',\n"
    "    (job_id, slurm_job_id, submitted_by, cpus, mem_mb),\n"
    ")"
)
pdf.body(
    "? placeholders are parameterised queries -- the sqlite3 driver handles escaping. "
    "This prevents SQL injection if submitted_by or any other field contained SQL syntax."
)

pdf.code(
    "SELECT job_id, slurm_job_id, submitted_by, submitted_at, cpus, mem_mb\n"
    "FROM jobs ORDER BY submitted_at DESC LIMIT ?"
)
pdf.body(
    "list_jobs deliberately excludes the output column. Output can be large (the entire "
    "stdout of a computation). Returning it for every job in a list would be slow and "
    "waste bandwidth. The client fetches output only when checking a specific job's status."
)

# ======================================================================
# 9. COORDINATOR/MAIN.PY
# ======================================================================
pdf._section_break()
pdf.section("9  coordinator/main.py")

pdf.code(
    "CTRL  = 'slurmctld'\n"
    "NODE  = 'node01'"
)
pdf.body(
    "The Docker container names used in every docker exec call. Named constants so "
    "renaming a container requires changing it in one place."
)

pdf.code(
    "def _exec(container, *cmd, stdin=None):\n"
    "    result = subprocess.run(\n"
    "        ['docker', 'exec', ('-i' if stdin is not None else ''), container, *cmd],\n"
    "        input=stdin, capture_output=True, text=True, timeout=30,\n"
    "    )"
)
pdf.bullets([
    "*cmd -- captures any number of positional arguments as a tuple. "
    "_exec(CTRL, 'rm', '-f', 'a', 'b') builds "
    "['docker','exec','','slurmctld','rm','-f','a','b'].",
    "'-i' flag -- opens stdin on the container side. Required when piping data in via "
    "stdin=. Without it the container process gets immediate EOF.",
    "input=stdin -- sends the string as stdin to the docker exec subprocess.",
    "capture_output=True -- captures stdout and stderr instead of printing to terminal.",
    "text=True -- decodes bytes to str automatically.",
    "timeout=30 -- raises TimeoutExpired if the command does not finish in 30 seconds, "
    "preventing the API from hanging if a container is stuck.",
])

pdf.code("cpus: int = max(1, min(int(body.get('cpus', 1)), 4))")
pdf.body(
    "body.get('cpus', 1) returns 1 if the key is absent. int(...) converts strings in "
    "case someone sends '2' instead of 2. min(..., 4) caps at 4 -- cannot request more "
    "than the node has. max(1, ...) prevents requesting 0 or negative CPUs."
)

pdf.code("job_id = secrets.token_hex(8)")
pdf.body(
    "secrets.token_hex(8) generates 8 random bytes and hex-encodes them to 16 characters. "
    "secrets (not random) uses the OS's cryptographic random source, so job IDs cannot "
    "be predicted or enumerated by an attacker."
)

pdf.code(
    "wrapper = f'''#!/bin/bash\n"
    "#SBATCH --job-name={job_id}\n"
    "#SBATCH --ntasks=1\n"
    "#SBATCH --cpus-per-task={cpus}\n"
    "#SBATCH --mem={mem_mb}M\n"
    "#SBATCH --output=/tmp/{job_id}.out\n"
    "#SBATCH --error=/tmp/{job_id}.out\n"
    "export WORK_INPUT='...'\n"
    "python3 /tmp/{job_id}.py\n"
    "'''"
)
pdf.bullets([
    "#SBATCH lines are read by sbatch as directives before the script runs.",
    "--ntasks=1 -- one process, not an MPI job.",
    "--cpus-per-task + SelectTypeParameters=CR_Core_Memory -- Slurm allocates exactly "
    "{cpus} specific cores and task/affinity pins the job to them via sched_setaffinity.",
    "--output and --error pointing to the same file merges stdout and stderr.",
    "Output goes to /tmp/{job_id}.out inside the node container -- not a mounted host path.",
    "WORK_INPUT -- input JSON set as an env var so the Python script reads it via "
    "os.environ['WORK_INPUT']. Single-quoted in bash so JSON double-quotes don't break "
    "shell syntax.",
])

pdf.code(
    "_exec(CTRL, 'bash', '-c',\n"
    "    f'cat > /tmp/{job_id}.py && chmod 600 /tmp/{job_id}.py',\n"
    "    stdin=script)"
)
pdf.body(
    "bash -c runs a shell command string inside the controller container. cat > writes "
    "stdin to the file. chmod 600 sets permissions to owner-read+write only (root owns "
    "it since docker exec runs as root). The && means chmod only runs if cat succeeded. "
    "stdin=script pipes the Python script text from the coordinator into the container "
    "without ever touching the host filesystem."
)

pdf.code(
    "out = _slurm('sbatch', '--uid=worker', f'/tmp/{job_id}.sh')\n"
    "slurm_job_id = out.split()[-1]"
)
pdf.body(
    "--uid=worker tells sbatch to submit the job on behalf of the worker user -- "
    "the job process will run as worker. sbatch prints 'Submitted batch job 42'. "
    ".split()[-1] gets the last token, '42'."
)

pdf.code("_exec(CTRL, 'rm', '-f', f'/tmp/{job_id}.sh', f'/tmp/{job_id}.py')")
pdf.body(
    "Deletes both temp files immediately after sbatch queues the job. At this point "
    "Slurm has already copied the script internally to SlurmdSpoolDir. Removing the "
    "files closes the window during which another process could read another user's "
    "input data. -f prevents rm from failing if a file does not exist."
)

pdf.code(
    "def _fetch_and_store_output(job):\n"
    "    if job.get('output') is not None:\n"
    "        return job['output']\n"
    "    output = _exec(NODE, 'cat', f'/tmp/{job[\"job_id\"]}.out')\n"
    "    _exec(NODE, 'rm', '-f', f'/tmp/{job[\"job_id\"]}.out')\n"
    "    db.store_output(job['job_id'], output)\n"
    "    return output"
)
pdf.bullets([
    "job.get('output') is not None -- short-circuits if output is already in the DB. "
    "Prevents repeatedly calling docker exec cat for the same finished job.",
    "_exec(NODE, 'cat', ...) -- runs inside node01, where slurmd wrote the output file.",
    "rm after cat -- deletes the file from the container once we have its content. "
    "Keeping it would allow other jobs (running as the same worker UID) to read it.",
    "db.store_output -- writes to SQLite. Future calls to get_job return from the DB.",
    "Returns None silently if the file does not exist yet (job may have just finished "
    "but file not flushed). The caller tries again on the next status poll.",
])

pdf.code(
    "job['slurm_state'] = _slurm(\n"
    "    'squeue', '-j', job['slurm_job_id'], '-h', '-o', '%T'\n"
    ") or 'COMPLETED'"
)
pdf.body(
    "squeue -j queries only that specific job. -h suppresses the header line. "
    "-o '%T' formats output as just the state string: PENDING, RUNNING, COMPLETED, "
    "FAILED, CANCELLED, or TIMEOUT. If squeue returns empty (job left the queue), "
    "or 'COMPLETED' defaults to COMPLETED."
)

# ======================================================================
# 10. COORDINATOR/CLIENT.PY
# ======================================================================
pdf._section_break()
pdf.section("10  coordinator/client.py")

pdf.code(
    "def _check(r):\n"
    "    try:\n"
    "        r.raise_for_status()\n"
    "    except requests.HTTPError:\n"
    "        detail = r.json().get('detail', r.text)\n"
    "        print(f'Error {r.status_code}: {detail}')\n"
    "        sys.exit(1)\n"
    "    return r.json()"
)
pdf.body(
    "raise_for_status() raises HTTPError for 4xx/5xx responses. The inner block "
    "extracts the 'detail' field from FastAPI's standard error JSON "
    "({'detail': 'Job not found'}). If the response is not JSON, falls back to raw text. "
    "sys.exit(1) terminates with a non-zero code so shell scripts can detect failure."
)

pdf.code(
    "DEFAULT_URL = 'http://localhost:8000'"
)
pdf.body(
    "Used if --url is not passed. When you expose the coordinator publicly in Phase 2, "
    "users pass --url https://compute.cornelltilde.com."
)

pdf.code("\"input\": json.loads(args.input) if args.input else {}")
pdf.body(
    "json.loads(args.input) parses --input '{\"x\":1}' into a Python dict. "
    "The if args.input else {} handles the case where --input was not provided."
)

pdf.code(
    "if not args.watch or state not in ('PENDING', 'RUNNING', 'UNKNOWN', ''):\n"
    "    break\n"
    "time.sleep(3)"
)
pdf.body(
    "The watch loop. not args.watch exits immediately if --watch was not passed. "
    "Otherwise exits once the state is anything other than an in-progress state. "
    "time.sleep(3) polls every 3 seconds."
)

pdf.code(
    "{\n"
    "    'submit': cmd_submit,\n"
    "    'status': cmd_status,\n"
    "    'jobs':   cmd_jobs,\n"
    "    'nodes':  cmd_nodes,\n"
    "    'queue':  cmd_queue,\n"
    "    'cancel': cmd_cancel,\n"
    "}[args.cmd](args, base)"
)
pdf.body(
    "Dictionary dispatch -- looks up the function by the command string and calls it. "
    "Cleaner than a chain of if/elif. ConnectionError (coordinator not running) is "
    "caught separately from HTTPError (coordinator running but returned an error)."
)

pdf.code(
    "p.add_argument('--cpus', type=int, default=1, help='CPU cores (max 4)')\n"
    "p.add_argument('--mem',  type=int, default=512, metavar='MB')"
)
pdf.body(
    "type=int makes argparse convert the string argument to an integer automatically "
    "and show a clear error if the user passes a non-integer. metavar='MB' changes the "
    "placeholder shown in --help from the default 'MEM' to 'MB'."
)

# ======================================================================
# 11. TILDE-NODE
# ======================================================================
pdf._section_break()
pdf.section("11  tilde-node")

pdf.code("set -euo pipefail")
pdf.body(
    "-e exits on error. -u errors on unset variables. -o pipefail makes a pipeline "
    "fail if any command in it fails, not just the last one."
)

pdf.code('SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"')
pdf.body(
    "${BASH_SOURCE[0]} is the path to this script itself (works even via symlinks). "
    "dirname extracts the directory portion. cd ... && pwd resolves it to an absolute "
    "path. This means you can run ./tilde-node start from any directory and it still "
    "finds slurm/docker-compose.yml relative to its own location."
)

pdf.code('_compose() { docker compose -f "$COMPOSE_FILE" "$@"; }')
pdf.body(
    'A shell function that prepends docker compose -f <path> to all arguments. '
    '"$@" expands to all arguments quoted individually. Every Docker Compose call '
    "uses the absolute path, not whatever the working directory happens to be."
)

pdf.code(
    "_wait_for_slurm() {\n"
    "    local tries=0\n"
    "    until docker exec slurmctld scontrol ping 2>/dev/null | grep -q 'UP'; do\n"
    "        tries=$((tries + 1))\n"
    "        if [ \"$tries\" -ge 40 ]; then exit 1; fi\n"
    "        sleep 3\n"
    "    done\n"
    "}"
)
pdf.body(
    "local tries=0 scopes the variable to the function. until loops while the "
    "condition is false. 40 tries x 3 seconds = 120-second timeout before giving up. "
    "Without a cap, a broken setup would poll forever."
)

pdf.code(
    "stop)\n"
    "    scontrol update NodeName=node01 State=DRAIN Reason='tilde-node stop' || true\n"
    "    sleep 5\n"
    "    _compose down"
)
pdf.body(
    "DRAIN state tells Slurm: accept no new jobs on this node, but let running jobs "
    "finish. || true makes the line succeed even if slurmctld is not responsive. "
    "sleep 5 gives in-flight jobs time to wrap up. _compose down stops and removes "
    "containers but leaves named volumes intact so state and logs persist for next start."
)

pdf.code(
    "logs)\n"
    "    _compose logs -f --tail=50"
)
pdf.body(
    "-f follows (streams new log lines as they appear). --tail=50 shows the last "
    "50 lines from each container first before following. Output is interleaved from "
    "both slurmctld and node01 containers, prefixed by container name."
)

# ======================================================================
# Output
# ======================================================================
pdf.output(OUT_PATH)
print(f"Written: {OUT_PATH}  ({pdf.page} pages)")
