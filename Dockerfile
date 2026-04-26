FROM alpine:3.20

# (opcional, mas recomendado pelo OpenClaw quando houver tretas com sharp/libvips)
ENV SHARP_IGNORE_GLOBAL_LIBVIPS=1

# Allow deterministic upgrades by pinning the OpenClaw npm version at build time.
ARG OPENCLAW_VERSION=latest
ARG GEMINI_CLI_VERSION=latest

# Dependências para o node-llama-cpp conseguir compilar o llama.cpp quando não houver binário compatível.
# Alpine evita o conjunto extra de ownerships do bookworm que quebra o build rootless.
RUN apk add --no-cache \
    bash \
    ca-certificates \
    curl \
    nodejs \
    npm \
    git \
    gh \
    sudo \
    cmake \
    build-base \
    linux-headers \
    python3 \
    ripgrep \
    pkgconf \
    chromium \
    libc6-compat \
    gcompat \
    ttf-liberation \
    noto-fonts-emoji \
 && update-ca-certificates

# Permite elevação local para o usuário node quando necessário em tarefas do workspace.
RUN echo "node ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/node \
 && chmod 440 /etc/sudoers.d/node

# Instala o OpenClaw e Gemini CLI (necessário para OAuth do provider google-gemini-cli)
RUN npm install -g "openclaw@${OPENCLAW_VERSION}" "@google/gemini-cli@${GEMINI_CLI_VERSION}"

# Rodar como usuário não-root (boa prática)
USER node
WORKDIR /home/node

ENTRYPOINT ["openclaw"]
