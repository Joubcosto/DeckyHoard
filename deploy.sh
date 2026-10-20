#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# deploy.sh — Build and deploy decky-hoard to SteamOS or Bazzite
#
# Usage:
#   ./deploy.sh                  Local deployment (when run directly on the Deck/PC)
#   ./deploy.sh deck@<IP>        Remote deployment from WSL / dev machine via SSH
# ==============================================================================

PLUGIN_NAME="decky-hoard"
PLUGIN_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors for terminal output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1. Compile the frontend
log_info "Building plugin frontend with pnpm..."
cd "${PLUGIN_DIR}"
pnpm run build

if [ ! -f "${PLUGIN_DIR}/dist/index.js" ]; then
    log_error "Build failed: dist/index.js not found!"
    exit 1
fi
log_success "Frontend bundle successfully generated in dist/index.js"

# 2. Check deployment mode
REMOTE_HOST="${1:-}"

if [ -n "${REMOTE_HOST}" ]; then
    # -------------------------------------------------------------------------
    # Remote SSH Deployment
    # -------------------------------------------------------------------------
    log_info "Deploying remotely to: ${REMOTE_HOST}"

    REMOTE_TMP="/tmp/${PLUGIN_NAME}"
    REMOTE_DEST="~/homebrew/plugins/${PLUGIN_NAME}"

    log_info "Creating temporary directory on remote host..."
    ssh "${REMOTE_HOST}" "mkdir -p ${REMOTE_TMP}"

    log_info "Syncing plugin files to ${REMOTE_TMP}..."
    rsync -avz --delete \
        --exclude 'node_modules' \
        --exclude '.git' \
        --exclude 'src' \
        --exclude 'tsconfig.json' \
        --exclude 'rollup.config.js' \
        "${PLUGIN_DIR}/" "${REMOTE_HOST}:${REMOTE_TMP}/"

    log_info "Installing to ${REMOTE_DEST} and restarting plugin_loader on ${REMOTE_HOST}..."
    ssh -t "${REMOTE_HOST}" "sudo mkdir -p ~/homebrew/plugins && sudo rm -rf ${REMOTE_DEST} && sudo cp -r ${REMOTE_TMP} ~/homebrew/plugins/ && sudo chmod -R 755 ${REMOTE_DEST} && rm -rf ${REMOTE_TMP} && sudo systemctl restart plugin_loader"

    log_success "Remote deployment complete! decky-hoard is active on ${REMOTE_HOST}"

else
    # -------------------------------------------------------------------------
    # Local Deployment (SteamOS / Bazzite)
    # -------------------------------------------------------------------------
    LOCAL_USER="${DECKY_USER:-${USER:-deck}}"
    HOME_DIR="${HOME:-/home/${LOCAL_USER}}"
    TARGET_DIR="${HOME_DIR}/homebrew/plugins/${PLUGIN_NAME}"

    if [ "${EUID}" -eq 0 ]; then
        SUDO=""
    else
        SUDO="sudo"
    fi

    log_info "Deploying locally to: ${TARGET_DIR}"

    if [ ! -d "${HOME_DIR}/homebrew/plugins" ]; then
        log_warn "${HOME_DIR}/homebrew/plugins does not exist. Creating directory..."
        ${SUDO} mkdir -p "${HOME_DIR}/homebrew/plugins"
    fi

    # Create target directory
    ${SUDO} mkdir -p "${TARGET_DIR}"

    # Copy files
    log_info "Copying plugin files..."
    ${SUDO} cp -r "${PLUGIN_DIR}/dist" "${TARGET_DIR}/"
    ${SUDO} cp "${PLUGIN_DIR}/main.py" "${TARGET_DIR}/"
    ${SUDO} cp "${PLUGIN_DIR}/plugin.json" "${TARGET_DIR}/"
    ${SUDO} cp "${PLUGIN_DIR}/package.json" "${TARGET_DIR}/"

    # Set appropriate ownership and permissions
    ${SUDO} chmod -R 755 "${TARGET_DIR}"

    log_info "Restarting Decky Loader (plugin_loader service)..."
    if command -v systemctl >/dev/null 2>&1; then
        ${SUDO} systemctl restart plugin_loader
        log_success "Plugin deployed and plugin_loader restarted successfully!"
    else
        log_warn "systemctl not found. Please restart Decky Loader manually."
    fi
fi
