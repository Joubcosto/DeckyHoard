# Hoard Sync (`decky-hoard`) — v0.5.0

Decky Loader plugin for [Hoard](https://github.com/rleeon/hoard) (game save backup and synchronization) designed specifically for SteamOS and Bazzite in Game Mode.

---

## Features

- **Automated CLI Setup**: One-click installation of the official `HoardSetup` binary with SHA-256 verification and proper unprivileged user permissions.
- **Background Sync Management**: "Sync Now" button that detects daemon state and starts or restarts `hoardd` (`hoard-sync.service`), triggering immediate synchronization.
- **Dynamic Steam Library Discovery**: Scans internal SSD and mounted MicroSD cards by parsing `libraryfolders.vdf` and `appmanifest_<appid>.acf`.
- **Hybrid Matching**: Merges Steam games with `hoard scan --json` to detect exact slugs and save paths.
- **One-Click Tracking**:
  - **Ready to track**: Verified games tracked via `hoard track --slug <slug>`.
  - **Other games**: Fallback for unlisted games via fuzzy search.
  - **Tracked games**: Visual green badge confirming active synchronization.
  - **Missing folders**: Collapsible section for games with no local save folder detected.
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
