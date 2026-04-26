#!/bin/bash
set -eu

# ── Wait for munge key (controller writes it to the shared volume first) ──────
echo "node01: waiting for munge key..."
until [ -s /etc/munge/munge.key ]; do sleep 1; done

chown munge:munge /etc/munge/munge.key
chmod 400 /etc/munge/munge.key
runuser -u munge -- munged
sleep 2

# ── State dirs ────────────────────────────────────────────────────────────────
mkdir -p /var/spool/slurmd /var/run/slurm /var/log/slurm
chown slurm:slurm /var/spool/slurmd /var/run/slurm /var/log/slurm

# ── Wait for slurmctld to accept connections ──────────────────────────────────
# slurmd will heartbeat slurmctld automatically once running; this just avoids
# the first-start race where slurmd tries to register before slurmctld is ready.
echo "node01: waiting for slurmctld..."
until scontrol ping 2>/dev/null | grep -q "UP\|is UP"; do sleep 3; done

# slurmd runs as root so it can set up cgroups and manage job processes.
# The jobs themselves run as 'worker' (set by the sbatch wrapper).
echo "node01: starting slurmd (4 CPUs, cgroup isolation)"
exec slurmd -D -N node01 -v
