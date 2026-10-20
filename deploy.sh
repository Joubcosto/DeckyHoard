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

    REMOTE_DEST="~/homebrew/plugins/${PLUGIN_NAME}"

    log_info "Creating remote plugin directory..."
    ssh "${REMOTE_HOST}" "mkdir -p ${REMOTE_DEST}"

    log_info "Syncing plugin files..."
    rsync -avz --delete \
        --exclude 'node_modules' \
        --exclude '.git' \
        --exclude 'src' \
        --exclude 'tsconfig.json' \
        --exclude 'rollup.config.js' \
        "${PLUGIN_DIR}/" "${REMOTE_HOST}:${REMOTE_DEST}/"

    log_info "Restarting plugin_loader service on ${REMOTE_HOST}..."
    ssh -t "${REMOTE_HOST}" "sudo systemctl restart plugin_loader"

    log_success "Remote deployment complete! decky-hoard is active on ${REMOTE_HOST}"

else
    # -------------------------------------------------------------------------
    # Local Deployment (SteamOS / Bazzite)
    # -------------------------------------------------------------------------
    LOCAL_USER="${DECKY_USER:-${USER:-deck}}"
    HOME_DIR="${HOME:-/home/${LOCAL_USER}}"
    TARGET_DIR="${HOME_DIR}/homebrew/plugins/${PLUGIN_NAME}"

    log_info "Deploying locally to: ${TARGET_DIR}"

    if [ ! -d "${HOME_DIR}/homebrew/plugins" ]; then
        log_warn "${HOME_DIR}/homebrew/plugins does not exist. Creating directory..."
        mkdir -p "${HOME_DIR}/homebrew/plugins"
    fi

    # Create target directory
    mkdir -p "${TARGET_DIR}"

    # Copy files
    log_info "Copying plugin files..."
    cp -r "${PLUGIN_DIR}/dist" "${TARGET_DIR}/"
    cp "${PLUGIN_DIR}/main.py" "${TARGET_DIR}/"
    cp "${PLUGIN_DIR}/plugin.json" "${TARGET_DIR}/"
    cp "${PLUGIN_DIR}/package.json" "${TARGET_DIR}/"

    # Set appropriate ownership and permissions
    chmod -R 755 "${TARGET_DIR}"

    log_info "Restarting Decky Loader (plugin_loader service)..."
    if command -v systemctl >/dev/null 2>&1; then
        if [ "${EUID}" -eq 0 ]; then
            systemctl restart plugin_loader
        else
            sudo systemctl restart plugin_loader
        fi
        log_success "Plugin deployed and plugin_loader restarted successfully!"
    else
        log_warn "systemctl not found. Please restart Decky Loader manually."
    fi
fi
