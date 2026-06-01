#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE_DIR="${BUNDLE_DIR:-${SCRIPT_DIR}/nvidia-container-toolkit-offline}"
PACKAGE_MANAGER="${PACKAGE_MANAGER:-auto}"

usage() {
  cat <<EOF
Usage:
  $(basename "$0") [--bundle-dir DIR] [--package-manager auto|apt|yum|dnf]

Run this script on an online machine with the same OS family, OS version,
and CPU architecture as the offline production host.

Options:
  --bundle-dir DIR                 Output directory for offline packages
  --package-manager auto|apt|yum|dnf
                                  Package manager to use, default: auto
  -h, --help                      Show this help message
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bundle-dir)
      BUNDLE_DIR="$2"
      shift 2
      ;;
    --package-manager)
      PACKAGE_MANAGER="$2"
      shift 2
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

detect_package_manager() {
  if [[ "${PACKAGE_MANAGER}" != "auto" ]]; then
    echo "${PACKAGE_MANAGER}"
    return
  fi

  if command -v apt-get >/dev/null 2>&1; then
    echo "apt"
    return
  fi

  if command -v dnf >/dev/null 2>&1; then
    echo "dnf"
    return
  fi

  if command -v yum >/dev/null 2>&1; then
    echo "yum"
    return
  fi

  echo "no supported package manager found; expected apt, dnf, or yum" >&2
  return 1
}

require_command() {
  local command_name="$1"

  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "required command not found: ${command_name}"
    exit 1
  fi
}

write_metadata() {
  mkdir -p "${BUNDLE_DIR}"

  if [[ -f /etc/os-release ]]; then
    cp /etc/os-release "${BUNDLE_DIR}/os-release.download-host"
  fi

  uname -m > "${BUNDLE_DIR}/arch.download-host"
  date -u +"%Y-%m-%dT%H:%M:%SZ" > "${BUNDLE_DIR}/created-at-utc.txt"
}

download_with_apt() {
  require_command curl
  require_command gpg
  require_command apt-get
  require_command apt-cache

  local deb_dir="${BUNDLE_DIR}/debs"
  mkdir -p "${deb_dir}"

  echo "configuring NVIDIA Container Toolkit apt repository"
  curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
    | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

  curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
    | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
    | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list >/dev/null

  sudo apt-get update

  local packages=(
    libnvidia-container1
    libnvidia-container-tools
    nvidia-container-toolkit-base
    nvidia-container-toolkit
  )

  echo "resolving apt dependencies"
  local package_list="${BUNDLE_DIR}/apt-packages.txt"
  apt-cache depends --recurse \
    --no-recommends \
    --no-suggests \
    --no-conflicts \
    --no-breaks \
    --no-replaces \
    --no-enhances \
    "${packages[@]}" \
    | awk '/^[[:alnum:]][[:alnum:].+:-]*$/ {print $1}' \
    | sort -u > "${package_list}"

  while IFS= read -r package_name; do
    if [[ -z "${package_name}" ]]; then
      continue
    fi

    if apt-cache show "${package_name}" >/dev/null 2>&1; then
      echo "downloading ${package_name}"
      (
        cd "${deb_dir}"
        apt-get download "${package_name}"
      )
    else
      echo "skipping unavailable apt package: ${package_name}"
    fi
  done < "${package_list}"

  echo "apt offline packages saved to: ${deb_dir}"
}

download_with_rpm() {
  local package_manager="$1"

  require_command curl
  require_command "${package_manager}"

  local rpm_dir="${BUNDLE_DIR}/rpms"
  mkdir -p "${rpm_dir}"

  echo "configuring NVIDIA Container Toolkit rpm repository"
  curl -s -L https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo \
    | sudo tee /etc/yum.repos.d/nvidia-container-toolkit.repo >/dev/null

  if [[ "${package_manager}" == "dnf" ]]; then
    if ! dnf download --help >/dev/null 2>&1; then
      echo "installing dnf download plugin"
      sudo dnf install -y dnf-plugins-core
    fi

    dnf download --resolve --alldeps --destdir="${rpm_dir}" nvidia-container-toolkit
  else
    if ! command -v yumdownloader >/dev/null 2>&1; then
      echo "installing yumdownloader"
      sudo yum install -y yum-utils
    fi

    yumdownloader --resolve --destdir="${rpm_dir}" nvidia-container-toolkit
  fi

  echo "rpm offline packages saved to: ${rpm_dir}"
}

main() {
  local package_manager
  package_manager="$(detect_package_manager)"

  case "${package_manager}" in
    apt)
      write_metadata
      download_with_apt
      ;;
    yum | dnf)
      write_metadata
      download_with_rpm "${package_manager}"
      ;;
    *)
      echo "unsupported package manager: ${package_manager}"
      usage
      exit 1
      ;;
  esac

  cp "${BASH_SOURCE[0]}" "${BUNDLE_DIR}/"
  if [[ -f "${SCRIPT_DIR}/install_nvidia_container_toolkit_offline.sh" ]]; then
    cp "${SCRIPT_DIR}/install_nvidia_container_toolkit_offline.sh" "${BUNDLE_DIR}/"
    chmod +x "${BUNDLE_DIR}/install_nvidia_container_toolkit_offline.sh"
  fi
  chmod +x "${BUNDLE_DIR}/$(basename "${BASH_SOURCE[0]}")"
  echo "${package_manager}" > "${BUNDLE_DIR}/package-manager.txt"

  cat <<EOF
done
bundle_dir=${BUNDLE_DIR}

Copy this whole directory to the offline production host, then run:

  sudo bash install_nvidia_container_toolkit_offline.sh --bundle-dir ${BUNDLE_DIR}
EOF
}

main "$@"
