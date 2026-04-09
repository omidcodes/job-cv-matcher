#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

DOCKER_CMD=()
COMPOSE_CMD=()
OLLAMA_STARTED_BY_SCRIPT="false"

log() {
  printf '\n[%s] %s\n' "$(date '+%H:%M:%S')" "$1"
}

fail() {
  printf '\nError: %s\n' "$1" >&2
  exit 1
}

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

require_sudo() {
  if ! command_exists sudo; then
    fail "sudo is required for this setup script."
  fi
}

wait_for_apt_lock() {
  if [[ "$(detect_os)" != "ubuntu" ]]; then
    return
  fi

  if ! command_exists fuser; then
    return
  fi

  local lock_files=(
    /var/lib/dpkg/lock-frontend
    /var/lib/dpkg/lock
    /var/cache/apt/archives/lock
    /var/lib/apt/lists/lock
  )

  local waited=false
  for _ in $(seq 1 120); do
    local locked=false
    for lock_file in "${lock_files[@]}"; do
      if sudo fuser "$lock_file" >/dev/null 2>&1; then
        locked=true
        break
      fi
    done

    if [[ "$locked" == "false" ]]; then
      return
    fi

    if [[ "$waited" == "false" ]]; then
      log "Waiting for Ubuntu package manager lock to clear"
      waited=true
    fi

    sleep 5
  done

  fail "Timed out waiting for the Ubuntu package manager lock. Please let the current apt/dpkg process finish, then rerun the script."
}

detect_os() {
  case "$(uname -s)" in
    Linux)
      if [[ -r /etc/os-release ]]; then
        # shellcheck disable=SC1091
        source /etc/os-release
        if [[ "${ID:-}" == "ubuntu" ]]; then
          echo "ubuntu"
          return
        fi
      fi
      fail "Unsupported Linux distribution. This script supports Ubuntu and macOS."
      ;;
    Darwin)
      echo "macos"
      ;;
    *)
      fail "Unsupported operating system."
      ;;
  esac
}

install_homebrew() {
  if command_exists brew; then
    return
  fi

  log "Installing Homebrew"
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

  if [[ -x /opt/homebrew/bin/brew ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [[ -x /usr/local/bin/brew ]]; then
    eval "$(/usr/local/bin/brew shellenv)"
  fi

  command_exists brew || fail "Homebrew installation completed, but brew is not on PATH."
}

install_ollama_macos() {
  if command_exists ollama; then
    log "Ollama is already installed"
    return
  fi

  log "Installing Ollama with Homebrew"
  brew install ollama
}

install_ollama_ubuntu() {
  if command_exists ollama; then
    log "Ollama is already installed"
    return
  fi

  log "Installing Ollama"
  curl -fsSL https://ollama.com/install.sh | sh
}

install_base_packages_ubuntu() {
  require_sudo
  wait_for_apt_lock

  log "Installing base packages"
  sudo apt-get update
  sudo apt-get install -y ca-certificates curl
}

install_docker_macos() {
  if command_exists docker; then
    log "Docker CLI is already installed"
  else
    log "Installing Docker Desktop with Homebrew"
    brew install --cask docker
  fi

  log "Starting Docker Desktop"
  open -a Docker >/dev/null 2>&1 || true
}

install_docker_ubuntu() {
  if command_exists docker; then
    log "Docker is already installed"
    return
  fi

  require_sudo
  log "Installing Docker Engine and Compose plugin"
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker "$USER" || true
}

wait_for_docker() {
  log "Waiting for Docker to become available"
  for _ in $(seq 1 60); do
    if docker info >/dev/null 2>&1; then
      DOCKER_CMD=(docker)
      return
    fi

    if command_exists sudo && sudo -n docker info >/dev/null 2>&1; then
      DOCKER_CMD=(sudo docker)
      return
    fi

    sleep 2
  done

  if command_exists sudo && sudo docker info >/dev/null 2>&1; then
    DOCKER_CMD=(sudo docker)
    return
  fi

  fail "Docker is installed but not ready. Start Docker Desktop on macOS or log out/in on Ubuntu if docker group access was just added."
}

ensure_docker_compose() {
  if "${DOCKER_CMD[@]}" compose version >/dev/null 2>&1; then
    COMPOSE_CMD=("${DOCKER_CMD[@]}" compose)
    return
  fi

  if command_exists docker-compose; then
    if docker-compose version >/dev/null 2>&1; then
      COMPOSE_CMD=(docker-compose)
      return
    fi

    if command_exists sudo && sudo docker-compose version >/dev/null 2>&1; then
      COMPOSE_CMD=(sudo docker-compose)
      return
    fi
  fi

  fail "Docker Compose is not available. Install the Docker Compose plugin or docker-compose and rerun the script."
}

start_ollama_service() {
  if curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    log "Ollama service is already running"
    return
  fi

  log "Starting Ollama service"
  nohup ollama serve >/tmp/job-cv-matcher-ollama.log 2>&1 &
  OLLAMA_STARTED_BY_SCRIPT="true"

  for _ in $(seq 1 30); do
    if curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
      return
    fi
    sleep 2
  done

  fail "Ollama was started but the API did not become ready."
}

pull_model() {
  log "Pulling Ollama model: tinyllama"
  ollama pull tinyllama
}

start_stack() {
  log "Starting application with Docker Compose"
  cd "${REPO_ROOT}"
  "${COMPOSE_CMD[@]}" up --build -d
}

print_next_steps() {
  printf '\nSetup complete.\n'
  printf 'Frontend: http://localhost:8501\n'
  printf 'Backend docs: http://localhost:8001/docs\n'
  if [[ "${OLLAMA_STARTED_BY_SCRIPT}" == "true" ]]; then
    printf 'Ollama log: /tmp/job-cv-matcher-ollama.log\n'
  fi
}

main() {
  local os
  os="$(detect_os)"

  case "${os}" in
    macos)
      install_homebrew
      install_docker_macos
      install_ollama_macos
      ;;
    ubuntu)
      install_base_packages_ubuntu
      install_docker_ubuntu
      install_ollama_ubuntu
      ;;
  esac

  wait_for_docker
  ensure_docker_compose
  start_ollama_service
  pull_model
  start_stack
  print_next_steps
}

main "$@"
