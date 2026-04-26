FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    slurmctld \
    slurmd \
    slurm-client \
    munge \
    python3 \
    python3-pip \
    gosu \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Directories Slurm daemons write to
RUN mkdir -p /var/spool/slurmctld /var/spool/slurmd /var/run/slurm /var/log/slurm /jobs/output \
    && chown slurm:slurm /var/spool/slurmctld /var/spool/slurmd /var/run/slurm /var/log/slurm

# Unprivileged user that owns job processes inside the container.
# The coordinator submits jobs as this user via `docker exec -u worker`.
RUN useradd -m -s /bin/bash worker \
    && chown worker:worker /jobs /jobs/output

COPY entrypoints/ /entrypoints/
RUN chmod +x /entrypoints/*.sh
