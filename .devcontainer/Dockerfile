# Use the same Python base (Debian bookworm)
FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm

# Remove problematic Yarn repo (from earlier fix)
RUN rm -f /etc/apt/sources.list.d/yarn.list || true

# Install newer Node.js 20.x (LTS) via nodesource repo
# This gives you Node 20 + modern npm (10.x)
RUN apt-get update && apt-get install -y curl ca-certificates gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" > /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Optional: verify versions after install
RUN node --version && npm --version

# Install other packages you need
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
       git \
       build-essential \
       graphviz \
    && rm -rf /var/lib/apt/lists/*

# Switch to non-root user
USER vscode

# Set workdir
WORKDIR /workspace

# Install Python deps
RUN pip install --upgrade pip \
    && pip install \
       django \
       graphene-django \
       neomodel \
       django-neomodel \
       django-htmx