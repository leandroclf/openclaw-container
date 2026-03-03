FROM node:22-bookworm

# (opcional, mas recomendado pelo OpenClaw quando houver tretas com sharp/libvips)
ENV SHARP_IGNORE_GLOBAL_LIBVIPS=1

# Allow deterministic upgrades by pinning the OpenClaw npm version at build time.
ARG OPENCLAW_VERSION=latest
ARG GEMINI_CLI_VERSION=latest

# Dependências para o node-llama-cpp conseguir compilar o llama.cpp quando não houver binário compatível
RUN apt-get update -o Acquire::Retries=3 -o Acquire::http::Timeout=30 \
 && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    gh \
    sudo \
    cmake \
    build-essential \
    python3 \
    python3.11-venv \
    python-is-python3 \
    ripgrep \
    pkg-config \
    chromium \
    fonts-liberation \
    fonts-noto-color-emoji \
 && rm -rf /var/lib/apt/lists/*

# Permite elevação local para o usuário node quando necessário em tarefas do workspace.
RUN usermod -aG sudo node \
 && echo "node ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/node \
 && chmod 440 /etc/sudoers.d/node

# Instala o OpenClaw e Gemini CLI (necessário para OAuth do provider google-gemini-cli)
RUN npm install -g "openclaw@${OPENCLAW_VERSION}" "@google/gemini-cli@${GEMINI_CLI_VERSION}"

# Rodar como usuário não-root (boa prática)
USER node
WORKDIR /home/node

ENTRYPOINT ["openclaw"]
