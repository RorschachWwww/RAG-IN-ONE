#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE_DIR="${BUNDLE_DIR:-${SCRIPT_DIR}/nvidia-container-toolkit-offline}"
CONFIGURE_DOCKER="${CONFIGURE_DOCKER:-true}"

usage() {
  cat <<EOF
Usage:
  sudo $(basename "$0") [--bundle-dir DIR] [--no-configure-docker]

Run this script on the offline production host after copying the offline bundle
created by download_nvidia_container_toolkit_offline.sh.

Options:
  --bundle-dir DIR       Directory that contains debs/ or rpms/
  --no-configure-docker  Install packages only, do not configure/restart Docker
  -h, --help             Show this help message
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bundle-dir)
      BUNDLE_DIR="$2"
      shift 2
      ;;
    --no-configure-docker)
      CONFIGURE_DOCKER=false
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown argument: $1"
      usage
      exit 1
      ;;
  esac
done

if [[ "$(id -u)" -ne 0 ]]; then
  echo "please run as root, for example:"
  echo "  sudo bash $0 --bundle-dir ${BUNDLE_DIR}"
  exit 1
fi

if [[ ! -d "${BUNDLE_DIR}" ]]; then
  echo "bundle dir not found: ${BUNDLE_DIR}"
  exit 1
fi

show_host_warning() {
  if [[ -f "${BUNDLE_DIR}/os-release.download-host" && -f /etc/os-release ]]; then
    echo "download host os-release:"
    grep -E '^(ID|VERSION_ID|PRETTY_NAME)=' "${BUNDLE_DIR}/os-release.download-host" || true
    echo "production host os-release:"
    grep -E '^(ID|VERSION_ID|PRETTY_NAME)=' /etc/os-release || true
  fi

  if [[ -f "${BUNDLE_DIR}/arch.download-host" ]]; then
    local download_arch
    local production_arch
    download_arch="$(cat "${BUNDLE_DIR}/arch.download-host")"
    production_arch="$(uname -m)"

    if [[ "${download_arch}" != "${production_arch}" ]]; then
      echo "architecture mismatch: download=${download_arch}, production=${production_arch}"
      exit 1
    fi
  fi
}

install_debs() {
  local deb_dir="${BUNDLE_DIR}/debs"

  if [[ ! -d "${deb_dir}" ]]; then
    echo "deb directory not found: ${deb_dir}"
    exit 1
  fi

  if ! compgen -G "${deb_dir}/*.deb" >/dev/null 2>&1; then
    echo "no .deb files found in: ${deb_dir}"
    exit 1
  fi

  echo "installing deb packages from: ${deb_dir}"
  apt-get install -y "${deb_dir}"/*.deb
}

install_rpms() {
  local rpm_dir="${BUNDLE_DIR}/rpms"

  if [[ ! -d "${rpm_dir}" ]]; then
    echo "rpm directory not found: ${rpm_dir}"
    exit 1
  fi

  if ! compgen -G "${rpm_dir}/*.rpm" >/dev/null 2>&1; then
    echo "no .rpm files found in: ${rpm_dir}"
    exit 1
  fi

  echo "installing rpm packages from: ${rpm_dir}"
  if command -v dnf >/dev/null 2>&1; then
    dnf install -y "${rpm_dir}"/*.rpm
  elif command -v yum >/dev/null 2>&1; then
    yum localinstall -y "${rpm_dir}"/*.rpm
  else
    rpm -Uvh "${rpm_dir}"/*.rpm
  fi
}

configure_docker() {
  if [[ "${CONFIGURE_DOCKER}" != "true" ]]; then
    echo "skipped Docker configuration"
    return
  fi

  if ! command -v nvidia-ctk >/dev/null 2>&1; then
    echo "nvidia-ctk command not found after package installation"
    exit 1
  fi

  if ! command -v docker >/dev/null 2>&1; then
    echo "docker command not found; install Docker first or rerun with --no-configure-docker"
    exit 1
  fi

  echo "configuring Docker NVIDIA runtime"
  nvidia-ctk runtime configure --runtime=docker

  if command -v systemctl >/dev/null 2>&1; then
    systemctl restart docker
  elif command -v service >/dev/null 2>&1; then
    service docker restart
  else
    echo "could not restart Docker automatically; please restart Docker manually"
  fi
}

verify_installation() {
  echo "installed NVIDIA container tools:"
  command -v nvidia-ctk || true
  command -v nvidia-container-runtime || true

  if command -v nvidia-ctk >/dev/null 2>&1; then
    nvidia-ctk --version || true
  fi

  cat <<EOF
next check:

  nvidia-smi
  docker run --rm --gpus all rag-in-one/bge-m3-embed:latest python -c "import torch; print(torch.cuda.is_available(), torch.cuda.device_count())"

If Docker still reports a CDI/vendor error, generate CDI spec and use DOCKER_GPU_MODE=cdi:

  sudo nvidia-ctk cdi generate --output=/etc/cdi/nvidia.yaml
  nvidia-ctk cdi list
EOF
}

main() {
  show_host_warning

  if [[ -d "${BUNDLE_DIR}/debs" ]]; then
    install_debs
  elif [[ -d "${BUNDLE_DIR}/rpms" ]]; then
    install_rpms
  else
    echo "bundle must contain either debs/ or rpms/: ${BUNDLE_DIR}"
    exit 1
  fi

  configure_docker
  verify_installation
}

main "$@"
