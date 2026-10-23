# Hoard Sync (`decky-hoard`) — v0.5.0

Decky Loader plugin for [Hoard](https://github.com/rleeon/hoard) (game save backup and synchronization) designed specifically for SteamOS and Bazzite in Game Mode.

---

## Features

- **Minimal Hoard CLI Wrapper**: Relies 100% on Hoard's native `--json` CLI contract (`hoard scan --json`, `hoard saves --json`, `hoard whoami --json`) with clean `LD_LIBRARY_PATH` isolation for Decky Loader.
- **Headless CLI Setup**: One-click installation via Hoard's official `install.sh` (`HOARD_HEADLESS=1 HOARD_NONINTERACTIVE=1`).
- **Background Sync Management**: "Sync Now" button that ensures `hoard-sync.service` is running and triggers `hoard backup <save_id>` across active tracked saves.
- **One-Click Track & Untrack**:
  - **Tracked games**: Displays version badge (`vN` / `SYNCED`) and supports one-click local untracking (`hoard save untrack <save_id> --json`).
  - **Ready to track**: Games detected by `hoard scan --json` with valid save folders, tracked via `hoard track --slug <slug>`.
  - **Missing folders**: Collapsible section for installed games with no local save folder yet (`needs_folder: true`).
- **Game Mode UI**: Built with modern `@decky/api` (v1.x) and `@decky/ui` (v4.x), featuring bilingual FR/EN support matching the Steam client language and SteamOS toasts.

---

## Project Structure

```
DeckyHoard/
├── plugin.json         # Decky Loader plugin metadata
├── package.json        # Node dependencies (@decky/ui, @decky/api, react-icons)
├── tsconfig.json       # TypeScript configuration for Game Mode
├── rollup.config.js    # Rollup bundler setup
├── main.py             # Python backend service with non-root Hoard execution
├── src/
│   └── index.tsx       # React frontend component with i18n and categorized layout
├── deploy.sh           # Local & remote SSH deployment script
└── dist/
    └── index.js        # Compiled production frontend bundle
```

---

## Development & Deployment

### Build the frontend
```bash
pnpm install
pnpm run build
```

### Deploy locally (on Steam Deck / Bazzite)
```bash
chmod +x deploy.sh
./deploy.sh
```

### Deploy remotely (from PC / WSL to Steam Deck)
```bash
./deploy.sh deck@192.168.1.50
```

---

## License

AGPL-3.0 (matching the Hoard ecosystem).
