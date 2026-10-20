#!/usr/bin/env bash
set -euo pipefail

PLUGIN_NAME="decky-hoard"
ARCHIVE_NAME="${PLUGIN_NAME}.zip"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP_DIR="$(mktemp -d)"

trap 'rm -rf "${TMP_DIR}"' EXIT

cd "${SCRIPT_DIR}"

echo "Building frontend..."
pnpm run build

echo "Staging files into ${PLUGIN_NAME}/ root folder..."
mkdir -p "${TMP_DIR}/${PLUGIN_NAME}"
cp -r dist "${TMP_DIR}/${PLUGIN_NAME}/"
cp main.py package.json plugin.json "${TMP_DIR}/${PLUGIN_NAME}/"
[ -f LICENSE ] && cp LICENSE "${TMP_DIR}/${PLUGIN_NAME}/"
[ -f README.md ] && cp README.md "${TMP_DIR}/${PLUGIN_NAME}/"

rm -f "${SCRIPT_DIR}/${ARCHIVE_NAME}"

echo "Creating ${ARCHIVE_NAME}..."
(
    cd "${TMP_DIR}"
    if command -v zip >/dev/null 2>&1; then
        zip -r "${SCRIPT_DIR}/${ARCHIVE_NAME}" "${PLUGIN_NAME}"
    else
        python3 -m zipfile -c "${SCRIPT_DIR}/${ARCHIVE_NAME}" "${PLUGIN_NAME}"
    fi
)

echo "Archive created successfully: ${ARCHIVE_NAME}"
