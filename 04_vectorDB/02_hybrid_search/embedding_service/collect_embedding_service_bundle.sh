#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE_DIR="${BUNDLE_DIR:-${SCRIPT_DIR}/bundle_embedding_service}"
TAR_GLOB="${TAR_GLOB:-bge-m3-embed*.tar}"
SEARCH_DIR="${SEARCH_DIR:-$(pwd)}"

usage() {
  cat <<EOF
Usage:
  $(basename "$0") [--bundle-dir DIR] [--search-dir DIR] [--tar-glob PATTERN]

Options:
  --bundle-dir DIR   Target output directory for the bundle
  --search-dir DIR   Directory to search for image tar files
  --tar-glob PATTERN Filename glob for image tar files
  -h, --help         Show this help message
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --bundle-dir)
      BUNDLE_DIR="$2"
      shift 2
      ;;
    --search-dir)
      SEARCH_DIR="$2"
      shift 2
      ;;
    --tar-glob)
      TAR_GLOB="$2"
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

mkdir -p "${BUNDLE_DIR}"

copy_required_file() {
  local src="$1"
  local dst_dir="$2"

  if [[ ! -f "${src}" ]]; then
    echo "required file not found: ${src}"
    exit 1
  fi

  cp "${src}" "${dst_dir}/"
}

copy_required_file "${SCRIPT_DIR}/run_bge_m3_multi_gpu.sh" "${BUNDLE_DIR}"
copy_required_file "${SCRIPT_DIR}/docker-runtime.env" "${BUNDLE_DIR}"
copy_required_file "${SCRIPT_DIR}/README_PROD.md" "${BUNDLE_DIR}"
copy_required_file "${SCRIPT_DIR}/nginx.embedding.conf" "${BUNDLE_DIR}"
copy_required_file "${SCRIPT_DIR}/download_nvidia_container_toolkit_offline.sh" "${BUNDLE_DIR}"
copy_required_file "${SCRIPT_DIR}/install_nvidia_container_toolkit_offline.sh" "${BUNDLE_DIR}"

if compgen -G "${SEARCH_DIR}/${TAR_GLOB}" >/dev/null 2>&1; then
  for tar_file in "${SEARCH_DIR}"/${TAR_GLOB}; do
    cp "${tar_file}" "${BUNDLE_DIR}/"
    echo "copied image tar: ${tar_file}"
  done
else
  echo "no image tar matched ${SEARCH_DIR}/${TAR_GLOB}, skipped"
fi

cat > "${BUNDLE_DIR}/FILES.txt" <<'EOF'
Required files in this bundle:
- run_bge_m3_multi_gpu.sh
- docker-runtime.env
- README_PROD.md
- nginx.embedding.conf
- download_nvidia_container_toolkit_offline.sh
- install_nvidia_container_toolkit_offline.sh

Optional files:
- bge-m3-embed*.tar
EOF

chmod +x "${BUNDLE_DIR}/run_bge_m3_multi_gpu.sh"
chmod +x "${BUNDLE_DIR}/download_nvidia_container_toolkit_offline.sh"
chmod +x "${BUNDLE_DIR}/install_nvidia_container_toolkit_offline.sh"

echo "bundle created at: ${BUNDLE_DIR}"
ls -la "${BUNDLE_DIR}"
