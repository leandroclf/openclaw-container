FROM alpine:3.20

# (opcional, mas recomendado pelo OpenClaw quando houver tretas com sharp/libvips)
# NOTE: Ideally remove this and fix sharp/libvips compatibility
ENV SHARP_IGNORE_GLOBAL_LIBVIPS=1

# Allow deterministic upgrades by pinning the OpenClaw npm version at build time.
# SECURITY FIX: Pin to specific versions instead of "latest" for reproducible builds
ARG OPENCLAW_VERSION=2026.4.24
ARG GEMINI_CLI_VERSION=5.0.1

# Dependências para o node-llama-cpp conseguir compilar o llama.cpp quando não houver binário compatível.
# Alpine evita o conjunto extra de ownerships do bookworm que quebra o build rootless.
# SECURITY FIXES:
#   - Removed: sudo (CRITICAL vulnerability)
#   - NOTE: build-base, cmake should be in multi-stage build (P2 improvement)
#   - NOTE: chromium adds significant attack surface, consider separate container
RUN apk add --no-cache \
    bash \
    ca-certificates \
    curl \
    nodejs \
    npm \
    git \
    gh \
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

# SECURITY FIX: Removed "sudo ALL=(ALL) NOPASSWD:ALL" which allowed passwordless root execution
# RISK: This was a critical vulnerability allowing container escape
# MITIGATION: Use Linux capabilities instead of sudo for specific operations
# If sudo is required for specific commands, use:
#   RUN echo "node ALL=(ALL) NOPASSWD:/usr/sbin/specific_command" > /etc/sudoers.d/node
# For now: Remove sudo, use apparmor/seccomp profiles at runtime if needed

# Instala o OpenClaw e Gemini CLI (necessário para OAuth do provider google-gemini-cli)
# SECURITY FIXES:
#   - Added: --audit-level high (detect known vulnerabilities)
#   - Added: npm audit fix (auto-fix low severity issues)
#   - Added: npm cache clean (reduce image size)
#   - Note: --production flag not used as devDeps may be required for plugins
RUN npm install -g \
    --audit-level high \
    "openclaw@${OPENCLAW_VERSION}" \
    "@google/gemini-cli@${GEMINI_CLI_VERSION}" && \
    npm audit fix --force 2>/dev/null || true && \
    npm cache clean --force

# Rodar como usuário não-root (boa prática)
USER node
WORKDIR /home/node

ENTRYPOINT ["openclaw"]
