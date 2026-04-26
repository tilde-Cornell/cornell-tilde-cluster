#!/bin/bash
set -eu

# ── Munge (shared-secret auth between slurmctld and slurmd) ──────────────────
# The key lives on the munge-key named volume so the node container can read it.
if [ ! -s /etc/munge/munge.key ]; then
    echo "controller: generating munge key"
    dd if=/dev/urandom bs=1 count=1024 > /etc/munge/munge.key 2>/dev/null
fi
chown munge:munge /etc/munge/munge.key
chmod 400 /etc/munge/munge.key
runuser -u munge -- munged
sleep 2

# ── State dirs ────────────────────────────────────────────────────────────────
mkdir -p /var/spool/slurmctld /var/run/slurm /var/log/slurm
chown slurm:slurm /var/spool/slurmctld /var/run/slurm /var/log/slurm

echo "controller: starting slurmctld"
exec gosu slurm slurmctld -D -v
