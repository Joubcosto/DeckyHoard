import asyncio
import json
import logging
import os
import pwd
import re
import shutil
from typing import Any, Dict, List, Optional, Tuple

try:
    import decky
except ImportError:
    decky = None

if decky and hasattr(decky, "logger"):
    logger = decky.logger
else:
    logger = logging.getLogger("decky-hoard")
    logger.setLevel(logging.INFO)


def _get_decky_user_info() -> Tuple[str, int, int, str]:
    """Resolve the non-root SteamOS / Bazzite user (name, uid, gid, home)."""
    user_name: Optional[str] = getattr(decky, "DECKY_USER", None) if decky else None
    user_home: Optional[str] = getattr(decky, "DECKY_USER_HOME", None) if decky else None

    if not user_name or user_name == "root":
        user_name = os.environ.get("DECKY_USER") or os.environ.get("SUDO_USER")

    if not user_name or user_name == "root":
        m = re.match(r"^/var/home/([^/]+)|^/home/([^/]+)", os.path.abspath(__file__))
        if m:
            candidate = m.group(1) or m.group(2)
            try:
                if pwd.getpwnam(candidate).pw_uid >= 1000:
                    user_name = candidate
            except KeyError:
                pass

    if not user_name or user_name == "root":
        try:
            user_name = pwd.getpwnam("deck").pw_name
        except KeyError:
            for entry in pwd.getpwall():
                if entry.pw_uid >= 1000 and "home" in entry.pw_dir:
                    user_name = entry.pw_name
                    break

    entry = pwd.getpwnam(user_name) if user_name else pwd.getpwuid(os.getuid())
    if not user_home or user_home == "/root":
        user_home = entry.pw_dir

    return entry.pw_name, entry.pw_uid, entry.pw_gid, user_home


def _get_user_env(user_name: str, user_uid: int, user_home: str) -> Dict[str, str]:
    """
    Build a clean environment for the target user.
    Strips Decky Loader's PyInstaller LD_LIBRARY_PATH / LD_PRELOAD so native
    system binaries (hoard, systemctl, curl) use host libraries properly.
    """
    runtime_dir = f"/run/user/{user_uid}"
    real_home = os.path.realpath(user_home)

    env = dict(os.environ)
    env.pop("LD_LIBRARY_PATH", None)
    env.pop("LD_PRELOAD", None)

    env.update({
        "USER": user_name,
        "LOGNAME": user_name,
        "HOME": user_home,
        "XDG_CONFIG_HOME": os.path.join(user_home, ".config"),
        "XDG_DATA_HOME": os.path.join(user_home, ".local", "share"),
        "XDG_STATE_HOME": os.path.join(user_home, ".local", "state"),
        "XDG_CACHE_HOME": os.path.join(user_home, ".cache"),
        "XDG_RUNTIME_DIR": runtime_dir,
        "DBUS_SESSION_BUS_ADDRESS": f"unix:path={runtime_dir}/bus",
        "NO_COLOR": "1",
        "HOARD_NONINTERACTIVE": "1",
        "PATH": f"{user_home}/.local/bin:{real_home}/.local/bin:/usr/local/bin:/usr/bin:/bin",
    })
    return env


class HoardBackend:
    """Minimal CLI wrapper around `hoard` using its native `--json` contract."""

    def __init__(self):
        self._lock: Optional[asyncio.Lock] = None
        self._scan_lock: Optional[asyncio.Lock] = None
        self._user_name, self._user_uid, self._user_gid, self._user_home = _get_decky_user_info()
        self._hoard_bin = os.path.join(self._user_home, ".local", "bin", "hoard")
        self._cached_games: Optional[Dict[str, Any]] = None
        self._is_scanning = False
        logger.info(f"HoardBackend initialized for {self._user_name} ({self._user_home})")

    @property
    def lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    @property
    def scan_lock(self) -> asyncio.Lock:
        if self._scan_lock is None:
            self._scan_lock = asyncio.Lock()
        return self._scan_lock

    def _resolve_hoard_bin(self) -> str:
        if os.path.isfile(self._hoard_bin) and os.access(self._hoard_bin, os.X_OK):
            return self._hoard_bin
        env = _get_user_env(self._user_name, self._user_uid, self._user_home)
        found = shutil.which("hoard", path=env["PATH"])
        if found:
            self._hoard_bin = found
        return self._hoard_bin

    async def _exec(self, *cmd: str, timeout: int = 60) -> Dict[str, Any]:
        """Run a subprocess directly as DECKY_USER without a login shell wrapper."""
        env = _get_user_env(self._user_name, self._user_uid, self._user_home)
        kwargs: Dict[str, Any] = {
            "stdin": asyncio.subprocess.DEVNULL,
            "stdout": asyncio.subprocess.PIPE,
            "stderr": asyncio.subprocess.PIPE,
            "env": env,
            "cwd": self._user_home,
        }
        if os.geteuid() == 0:
            kwargs["user"] = self._user_uid
            kwargs["group"] = self._user_gid

        try:
            proc = await asyncio.create_subprocess_exec(*cmd, **kwargs)
            stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            return {
                "ok": proc.returncode == 0,
                "returncode": proc.returncode,
                "stdout": stdout_b.decode("utf-8", errors="replace").strip(),
                "stderr": stderr_b.decode("utf-8", errors="replace").strip(),
            }
        except asyncio.TimeoutError:
            logger.error(f"Command timed out ({timeout}s): {cmd}")
            return {"ok": False, "returncode": -2, "stdout": "", "stderr": f"Timed out after {timeout}s"}
        except FileNotFoundError:
            return {"ok": False, "returncode": 127, "stdout": "", "stderr": f"Binary not found: {cmd[0]}"}
        except Exception as e:
            logger.exception(f"Subprocess error ({cmd}): {e}")
            return {"ok": False, "returncode": -3, "stdout": "", "stderr": str(e)}

    async def _run_hoard(self, *args: str, timeout: int = 60) -> Dict[str, Any]:
        """
        Execute `hoard <args>` and parse Hoard's JSON envelope when `--json` is used:
        Success: {"ok": true, "data": ...}
        Error:   {"ok": false, "error": {"code": "...", "message": "..."}}
        """
        hoard_bin = self._resolve_hoard_bin()
        if not (os.path.isfile(hoard_bin) and os.access(hoard_bin, os.X_OK)):
            return {
                "ok": False,
                "returncode": 127,
                "error_code": "not_installed",
                "message": "Hoard CLI is not installed",
                "data": None,
            }

        res = await self._exec(hoard_bin, *args, timeout=timeout)
        stdout = res["stdout"]
        stderr = res["stderr"]
        rc = res["returncode"]

        envelope = None
        if stdout.startswith("{"):
            try:
                envelope = json.loads(stdout)
            except Exception:
                pass

        if isinstance(envelope, dict) and "ok" in envelope:
            if envelope.get("ok"):
                return {
                    "ok": True,
                    "returncode": rc,
                    "data": envelope.get("data"),
                    "stdout": stdout,
                    "stderr": stderr,
                }
            err_obj = envelope.get("error") if isinstance(envelope.get("error"), dict) else {}
            return {
                "ok": False,
                "returncode": rc,
                "error_code": err_obj.get("code", "cli_error"),
                "message": err_obj.get("message") or stderr or stdout,
                "data": None,
                "stdout": stdout,
                "stderr": stderr,
            }

        return {
            "ok": rc == 0,
            "returncode": rc,
            "error_code": None if rc == 0 else "cli_error",
            "message": stderr or stdout,
            "data": None,
            "stdout": stdout,
            "stderr": stderr,
        }

    async def get_status(self) -> Dict[str, Any]:
        """Check CLI installation, background daemon status, and user session."""
        hoard_bin = self._resolve_hoard_bin()
        if not (os.path.isfile(hoard_bin) and os.access(hoard_bin, os.X_OK)):
            return {
                "installed": False,
                "version": None,
                "logged_in": False,
                "user_info": None,
                "service_running": False,
                "is_scanning": self._is_scanning,
                "binary_path": hoard_bin,
            }

        ver_res, svc_res, whoami_res = await asyncio.gather(
            self._run_hoard("--version", timeout=5),
            self._exec("systemctl", "--user", "is-active", "hoard-sync.service", timeout=5),
            self._run_hoard("whoami", "--json", timeout=10),
        )

        version = ver_res["stdout"] if ver_res["ok"] else "Installed"
        service_running = svc_res["ok"] and svc_res["stdout"] == "active"

        # Hoard CLI exit code 2 / error_code "no_session" or "unauthorized" means signed out.
        # Exit code 6 ("network", "storage_unreachable") means signed in locally, but offline.
        err_code = whoami_res.get("error_code")
        rc = whoami_res.get("returncode")
        if whoami_res["ok"]:
            logged_in = True
            user_info = whoami_res.get("data")
        elif err_code in ("no_session", "unauthorized") or rc == 2:
            logged_in = False
            user_info = None
        else:
            logged_in = service_running or err_code in ("network", "storage_unreachable") or rc == 6
            user_info = None

        return {
            "installed": True,
            "version": version,
            "logged_in": logged_in,
            "user_info": user_info,
            "service_running": service_running,
            "is_scanning": self._is_scanning,
            "binary_path": hoard_bin,
        }

    async def install_hoard(self) -> Dict[str, Any]:
        """Install Hoard CLI in headless mode using the official installer script."""
        async with self.lock:
            script_url = "https://raw.githubusercontent.com/rleeon/hoard/main/web/static/install.sh"
            cmd = f"curl -fsSL {script_url} | HOARD_HEADLESS=1 HOARD_NONINTERACTIVE=1 sh"
            logger.info("Installing Hoard CLI via official install.sh (--headless)...")
            res = await self._exec("/bin/sh", "-c", cmd, timeout=300)

            hoard_bin = self._resolve_hoard_bin()
            if res["ok"] and os.path.isfile(hoard_bin):
                return {"ok": True, "message": "Hoard CLI installed successfully!"}

            err_msg = res["stderr"] or res["stdout"] or "Installer exited with an error"
            logger.error(f"Hoard install failed: {err_msg}")
            return {"ok": False, "message": err_msg}

    async def _get_tracked_saves(self) -> List[Dict[str, Any]]:
        """Read local tracked saves via `hoard saves --json` (offline & instant)."""
        res = await self._run_hoard("saves", "--json", timeout=15)
        if not res["ok"] or not isinstance(res.get("data"), dict):
            return []
        saves = res["data"].get("saves", [])
        return [s for s in saves if isinstance(s, dict)]

    async def force_sync(self) -> Dict[str, Any]:
        """Ensure hoard-sync service is running and trigger backup for all active saves."""
        async with self.lock:
            status = await self.get_status()
            if not status["installed"]:
                return {"ok": False, "message": "Hoard is not installed"}

            if not status["service_running"]:
                await self._run_hoard("sync", "start", timeout=20)

            saves = await self._get_tracked_saves()
            active_saves = [s for s in saves if s.get("save_id") and not s.get("paused")]

            backed_up = 0
            errors: List[str] = []
            for s in active_saves:
                b_res = await self._run_hoard("backup", str(s["save_id"]), timeout=180)
                if b_res["ok"]:
                    backed_up += 1
                else:
                    errors.append(b_res.get("message") or "Backup failed")

            if errors and backed_up == 0:
                return {"ok": False, "message": errors[0]}

            return {
                "ok": True,
                "message": f"Synchronized {backed_up}/{len(active_saves)} tracked save(s).",
            }

    async def track_game(self, game_name: str, slug: Optional[str] = None) -> Dict[str, Any]:
        """Track a detected game via `hoard track` and upload its first snapshot."""
        async with self.lock:
            args = ["track", "--slug", slug] if slug else ["track", game_name]
            res = await self._run_hoard(*args, timeout=120)

            if not res["ok"]:
                return {"ok": False, "message": res.get("message") or f"Could not track {game_name}"}

            # Extract save_id from `hoard track` output or `hoard saves --json`
            m = re.search(r"save_id:\s*([0-9a-fA-F-]{36}|\S+)", res.get("stdout", ""))
            save_id = m.group(1).strip() if m else None

            if not save_id and slug:
                for s in await self._get_tracked_saves():
                    if s.get("game_slug") == slug:
                        save_id = s.get("save_id")
                        break

            if save_id:
                await self._run_hoard("backup", str(save_id), timeout=180)

            self._cached_games = None
            return {
                "ok": True,
                "message": f"'{game_name}' is now tracked!",
                "slug": slug,
                "save_id": save_id,
            }

    async def untrack_game(self, save_id: str) -> Dict[str, Any]:
        """Stop watching a save folder locally while keeping cloud snapshots intact."""
        async with self.lock:
            res = await self._run_hoard("save", "untrack", save_id, "--json", timeout=30)
            if res["ok"]:
                self._cached_games = None
                return {"ok": True, "message": "Game untracked locally (cloud backups kept)."}
            return {"ok": False, "message": res.get("message") or "Failed to untrack game"}

    async def get_games(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Discover games exclusively through Hoard's native commands:
        - `hoard saves --json` (local tracked saves with save_id & version info)
        - `hoard scan --json`  (local Steam / Proton / Ludusavi detection)
        """
        async with self.scan_lock:
            if self._cached_games and not force_refresh:
                return self._cached_games

            self._is_scanning = True
            try:
                saves_list, scan_res = await asyncio.gather(
                    self._get_tracked_saves(),
                    self._run_hoard("scan", "--json", timeout=180),
                )

                saves_by_slug: Dict[str, Dict[str, Any]] = {}
                saves_by_path: Dict[str, Dict[str, Any]] = {}
                for s in saves_list:
                    g_slug = str(s.get("game_slug") or "").strip()
                    l_path = str(s.get("local_path") or "").strip()
                    if g_slug:
                        saves_by_slug[g_slug] = s
                    if l_path:
                        saves_by_path[l_path] = s

                scan_games: List[Dict[str, Any]] = []
                if scan_res["ok"] and isinstance(scan_res.get("data"), dict):
                    raw_games = scan_res["data"].get("games") or []
                    scan_games = [g for g in raw_games if isinstance(g, dict)]

                ready_to_track: List[Dict[str, Any]] = []
                tracked: List[Dict[str, Any]] = []
                missing_folder: List[Dict[str, Any]] = []
                seen_slugs: set = set()

                for g in scan_games:
                    slug = str(g.get("slug") or "").strip()
                    if not slug:
                        continue
                    seen_slugs.add(slug)

                    name = str(g.get("display_name") or slug)
                    paths = g.get("paths") if isinstance(g.get("paths"), list) else []
                    needs_folder = bool(g.get("needs_folder"))

                    save_entry = saves_by_slug.get(slug) or next(
                        (saves_by_path[p] for p in paths if p in saves_by_path), None
                    )
                    is_tracked = bool(g.get("tracked")) or (save_entry is not None)

                    item = {
                        "name": name,
                        "slug": slug,
                        "save_id": save_entry.get("save_id") if save_entry else None,
                        "paused": bool(save_entry.get("paused")) if save_entry else False,
                        "last_version_num": save_entry.get("last_version_num") if save_entry else None,
                        "last_backup_at": save_entry.get("last_backup_at") if save_entry else None,
                        "needs_folder": needs_folder,
                        "paths": paths,
                        "tracked": is_tracked,
                    }

                    if is_tracked:
                        tracked.append(item)
                    elif needs_folder:
                        missing_folder.append(item)
                    else:
                        ready_to_track.append(item)

                # Include any tracked saves from `hoard saves --json` not returned by `hoard scan`
                for s in saves_list:
                    slug = str(s.get("game_slug") or "").strip()
                    if not slug or slug in seen_slugs:
                        continue
                    seen_slugs.add(slug)
                    l_path = str(s.get("local_path") or "").strip()
                    tracked.append({
                        "name": slug,
                        "slug": slug,
                        "save_id": s.get("save_id"),
                        "paused": bool(s.get("paused")),
                        "last_version_num": s.get("last_version_num"),
                        "last_backup_at": s.get("last_backup_at"),
                        "needs_folder": False,
                        "paths": [l_path] if l_path else [],
                        "tracked": True,
                    })

                ready_to_track.sort(key=lambda x: x["name"].lower())
                tracked.sort(key=lambda x: x["name"].lower())
                missing_folder.sort(key=lambda x: x["name"].lower())

                result = {
                    "ready_to_track": ready_to_track,
                    "tracked": tracked,
                    "missing_folder": missing_folder,
                    "summary": {
                        "total": len(ready_to_track) + len(tracked) + len(missing_folder),
                        "ready_count": len(ready_to_track),
                        "tracked_count": len(tracked),
                        "missing_count": len(missing_folder),
                    },
                }
                self._cached_games = result
                return result
            finally:
                self._is_scanning = False


_backend: Optional[HoardBackend] = None


def _get_backend() -> HoardBackend:
    global _backend
    if _backend is None:
        _backend = HoardBackend()
    return _backend


class Plugin:
    async def _main(self):
        logger.info("Hoard plugin loaded.")
        asyncio.create_task(_get_backend().get_games(force_refresh=False))

    async def _unload(self):
        logger.info("Hoard plugin unloaded.")

    async def get_status(self) -> Dict[str, Any]:
        return await _get_backend().get_status()

    async def install_hoard(self) -> Dict[str, Any]:
        return await _get_backend().install_hoard()

    async def force_sync(self) -> Dict[str, Any]:
        return await _get_backend().force_sync()

    async def track_game(self, game_name: str, slug: Optional[str] = None) -> Dict[str, Any]:
        return await _get_backend().track_game(game_name, slug)

    async def untrack_game(self, save_id: str) -> Dict[str, Any]:
        return await _get_backend().untrack_game(save_id)

    async def get_games(self, force_refresh: bool = False) -> Dict[str, Any]:
        return await _get_backend().get_games(force_refresh)
