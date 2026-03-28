#!/usr/bin/env bash

docker_guard_available() {
  docker info >/dev/null 2>&1
}

docker_guard_try_start() {
  if command -v systemctl >/dev/null 2>&1; then
    systemctl start docker >/dev/null 2>&1 && return 0 || true
  fi

  if command -v service >/dev/null 2>&1; then
    service docker start >/dev/null 2>&1 && return 0 || true
  fi

  return 1
}

docker_guard_ensure() {
  local label="${1:-docker}"

  if docker_guard_available; then
    return 0
  fi

  echo "[$label] Docker daemon unavailable; attempting local service start" >&2
  docker_guard_try_start || true
  sleep "${DOCKER_GUARD_WAIT_SECONDS:-3}"

  if docker_guard_available; then
    echo "[$label] Docker daemon recovered" >&2
    return 0
  fi

  echo "[$label] Docker daemon still unavailable; continuing with local-only steps" >&2
  return 1
}

docker_guard_health_or_skip() {
  local container="${1:-openclaw}"
  local profile="${2:-prod}"
  local label="${3:-docker-health}"

  if docker_guard_available; then
    docker exec "$container" openclaw --profile "$profile" gateway health
    return $?
  fi

  echo "[$label] Docker unavailable; skipping gateway health check" >&2
  return 0
}
