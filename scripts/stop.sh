#!/usr/bin/env sh

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "${SCRIPT_DIR}/.." && pwd)

DOCKER_CMD=""
COMPOSE_CMD=""

log() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$1"
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

detect_os() {
  case "$(uname -s)" in
    Linux)
      if [ -r /etc/os-release ]; then
        # shellcheck disable=SC1091
        . /etc/os-release
        if [ "${ID:-}" = "ubuntu" ]; then
          echo "ubuntu"
          return
        fi
      fi
      echo "linux"
      ;;
    Darwin)
      echo "macos"
      ;;
    *)
      echo "other"
      ;;
  esac
}

detect_docker() {
  if command_exists docker && docker info >/dev/null 2>&1; then
    DOCKER_CMD="docker"
    return
  fi

  if command_exists sudo && sudo -n docker info >/dev/null 2>&1; then
    DOCKER_CMD="sudo docker"
    return
  fi

  if command_exists sudo && sudo docker info >/dev/null 2>&1; then
    DOCKER_CMD="sudo docker"
    return
  fi
}

detect_compose() {
  if [ -n "${DOCKER_CMD}" ] && ${DOCKER_CMD} compose version >/dev/null 2>&1; then
    COMPOSE_CMD="${DOCKER_CMD} compose"
    return
  fi

  if command_exists docker-compose && docker-compose version >/dev/null 2>&1; then
    COMPOSE_CMD="docker-compose"
    return
  fi

  if command_exists sudo && sudo docker-compose version >/dev/null 2>&1; then
    COMPOSE_CMD="sudo docker-compose"
    return
  fi
}

stop_project_compose() {
  if [ -z "${COMPOSE_CMD}" ]; then
    log "Docker Compose not found, skipping project stack shutdown"
    return
  fi

  log "Stopping project Docker Compose stack"
  (
    cd "${REPO_ROOT}"
    ${COMPOSE_CMD} down
  )
}

stop_all_running_containers() {
  if [ -z "${DOCKER_CMD}" ]; then
    log "Docker is not available, skipping container shutdown"
    return
  fi

  container_ids=$(${DOCKER_CMD} ps -q)

  if [ -z "${container_ids}" ]; then
    log "No running Docker containers found"
    return
  fi

  log "Stopping all running Docker containers"
  # shellcheck disable=SC2086
  ${DOCKER_CMD} stop ${container_ids}
}

stop_ollama_ubuntu() {
  if command_exists systemctl && systemctl is-active --quiet ollama; then
    log "Stopping Ollama systemd service"
    sudo systemctl stop ollama
    return
  fi

  if command_exists pkill; then
    log "Stopping local Ollama process"
    pkill -f "ollama serve" || true
  fi
}

stop_ollama_macos() {
  if command_exists pkill; then
    log "Stopping local Ollama process"
    pkill -f "ollama serve" || true
  fi
}

main() {
  os=$(detect_os)

  detect_docker
  detect_compose
  stop_project_compose
  stop_all_running_containers

  case "${os}" in
    ubuntu)
      stop_ollama_ubuntu
      ;;
    macos)
      stop_ollama_macos
      ;;
    *)
      stop_ollama_macos
      ;;
  esac

  printf '\nShutdown complete.\n'
}

main "$@"
