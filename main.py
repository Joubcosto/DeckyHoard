import asyncio
import hashlib
import json
import logging
import os
import pathlib
import pwd
import re
import shutil
import tempfile
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

# Attempt import of decky (available when running inside Decky Loader)
try:
    import decky
except ImportError:
    decky = None

logger = logging.getLogger("decky-hoard")
logger.setLevel(logging.INFO)

# Known Steam tool / runtime AppIDs to exclude from game list
EXCLUDED_APPIDS = {
    "228980",   # Steamworks Common Redistributables
    "1070560",  # Steam Linux Runtime
    "1391110",  # Steam Linux Runtime - Soldier
    "1628350",  # Steam Linux Runtime - Sniper
    "1826330",  # Steam Linux Runtime - Medic
    "221410",   # Steam Controller Configs
    "250820",   # SteamVR
    "896660",   # Proton 4.11
    "1245040",  # Proton 5.0
    "1420170",  # Proton 5.13
    "1580130",  # Proton 6.3
    "1887720",  # Proton 7.0
    "2348520",  # Proton 8.0
    "3089140",  # Proton 9.0
    "1493710",  # Proton Experimental
    "2180100",  # Proton Hotfix
}

# Prefix patterns for tools/runtimes to ignore
EXCLUDED_NAME_PATTERNS = [
    re.compile(r"^proton", re.IGNORECASE),
    re.compile(r"^steam linux runtime", re.IGNORECASE),
    re.compile(r"^steamworks common", re.IGNORECASE),
    re.compile(r"^steamvr", re.IGNORECASE),
    re.compile(r"^steam controller", re.IGNORECASE),
]


def _normalize_name(name: str) -> str:
    """Normalize game name for fuzzy comparison (remove punctuation, lower)."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _get_decky_user_info() -> Tuple[str, int, int, str]:
    """
    Determine target non-root user (name, uid, gid, home) for running Hoard.
    On SteamOS this is typically 'deck', on Bazzite the main user.
    """
    user_name: Optional[str] = None
    user_home: Optional[str] = None

    if decky:
        user_name = getattr(decky, "DECKY_USER", None)
        user_home = getattr(decky, "DECKY_USER_HOME", None)

    if not user_name:
        user_name = os.environ.get("DECKY_USER") or os.environ.get("SUDO_USER")

    # If still root or unset, look for 'deck' user or first UID >= 1000 with a home dir
    if not user_name or user_name == "root":
        try:
            deck_entry = pwd.getpwnam("deck")
            user_name = deck_entry.pw_name
            user_home = deck_entry.pw_dir
        except KeyError:
            for entry in pwd.getpwall():
                if entry.pw_uid >= 1000 and os.path.exists(entry.pw_dir) and "/home" in entry.pw_dir:
                    user_name = entry.pw_name
                    user_home = entry.pw_dir
                    break

    # Fallback to current process owner
    if not user_name:
        entry = pwd.getpwuid(os.getuid())
        user_name = entry.pw_name
        user_home = entry.pw_dir

    entry = pwd.getpwnam(user_name)
    user_uid = entry.pw_uid
    user_gid = entry.pw_gid
    if not user_home:
        user_home = entry.pw_dir

    return user_name, user_uid, user_gid, user_home


def _get_user_env(user_name: str, user_uid: int, user_home: str) -> Dict[str, str]:
    """Prepare environment variables needed by Hoard and systemd --user."""
    runtime_dir = f"/run/user/{user_uid}"
    bus_path = f"unix:path={runtime_dir}/bus"

    env = dict(os.environ)
    env["USER"] = user_name
    env["LOGNAME"] = user_name
    env["HOME"] = user_home
    env["XDG_RUNTIME_DIR"] = runtime_dir
    env["DBUS_SESSION_BUS_ADDRESS"] = bus_path
    bin_path = f"{user_home}/.local/bin"
    env["PATH"] = f"{bin_path}:/usr/local/bin:/usr/bin:/bin:{env.get('PATH', '')}"
    return env


class Plugin:
    def __init__(self):
        self._lock = asyncio.Lock()
        self._user_name, self._user_uid, self._user_gid, self._user_home = _get_decky_user_info()
        self._hoard_bin = os.path.join(self._user_home, ".local", "bin", "hoard")
        self._cached_games: Optional[Dict[str, Any]] = None
        self._is_scanning = False
        logger.info(
            f"Initialized decky-hoard for user={self._user_name} (uid={self._user_uid}), bin={self._hoard_bin}"
        )

    async def _main(self):
        logger.info("Hoard plugin loaded.")
        # Trigger an initial background scan without blocking startup
        asyncio.create_task(self.get_games(force_refresh=False))

    async def _unload(self):
        logger.info("Hoard plugin unloaded.")

    async def _run_hoard(self, *args: str, timeout: int = 60) -> Dict[str, Any]:
        """
        Execute the Hoard CLI as DECKY_USER with standard environment and stdin=DEVNULL.
        """
        if not os.path.exists(self._hoard_bin):
            return {
                "ok": False,
                "returncode": -1,
                "error": "not_installed",
                "message": f"Hoard binary not found at {self._hoard_bin}",
            }

        cmd = [self._hoard_bin, *args]
        env = _get_user_env(self._user_name, self._user_uid, self._user_home)

        # Drop privileges if currently running as root
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
            stdout_str = stdout_b.decode("utf-8", errors="replace").strip()
            stderr_str = stderr_b.decode("utf-8", errors="replace").strip()
            rc = proc.returncode

            data = None
            if stdout_str:
                try:
                    data = json.loads(stdout_str)
                except Exception:
                    data = None

            return {
                "ok": rc == 0,
                "returncode": rc,
                "stdout": stdout_str,
                "stderr": stderr_str,
                "data": data,
            }
        except asyncio.TimeoutError:
            logger.error(f"Command timed out ({timeout}s): {' '.join(cmd)}")
            return {
                "ok": False,
                "returncode": -2,
                "error": "timeout",
                "message": f"Command timed out after {timeout} seconds",
            }
        except Exception as e:
            logger.exception(f"Error running Hoard command {' '.join(cmd)}: {e}")
            return {
                "ok": False,
                "returncode": -3,
                "error": "exception",
                "message": str(e),
            }

    async def get_status(self) -> Dict[str, Any]:
        """
        Check Hoard installation status, user session (login), and background sync service.
        """
        installed = os.path.isfile(self._hoard_bin) and os.access(self._hoard_bin, os.X_OK)
        if not installed:
            return {
                "installed": False,
                "version": None,
                "logged_in": False,
                "user_info": None,
                "service_running": False,
                "is_scanning": self._is_scanning,
                "binary_path": self._hoard_bin,
            }

        # Check version
        version_res = await self._run_hoard("--version", timeout=10)
        version = version_res.get("stdout") if version_res["ok"] else "Installed"

        # Check session (hoard whoami --json)
        whoami_res = await self._run_hoard("whoami", "--json", timeout=15)
        logged_in = False
        user_info = None

        if whoami_res["ok"] and whoami_res.get("data"):
            logged_in = True
            user_info = whoami_res["data"].get("data")
        elif whoami_res.get("returncode") == 2:
            # Code 2 = no_session
            logged_in = False
            user_info = None

        # Check sync service via systemctl --user is-active hoard-sync.service
        service_running = False
        try:
            env = _get_user_env(self._user_name, self._user_uid, self._user_home)
            cmd = ["systemctl", "--user", "is-active", "hoard-sync.service"]
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

            proc = await asyncio.create_subprocess_exec(*cmd, **kwargs)
            stdout_b, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            status_text = stdout_b.decode("utf-8", errors="replace").strip()
            service_running = status_text == "active"
        except Exception as e:
            logger.warning(f"Error checking systemctl service: {e}")
            # Fallback to hoard sync status
            sync_res = await self._run_hoard("sync", timeout=5)
            service_running = "service: running" in (sync_res.get("stdout") or "")

        return {
            "installed": True,
            "version": version,
            "logged_in": logged_in,
            "user_info": user_info,
            "service_running": service_running,
            "is_scanning": self._is_scanning,
            "binary_path": self._hoard_bin,
        }

    async def install_hoard(self) -> Dict[str, Any]:
        """
        Download HoardSetup-x86_64, verify SHA256 checksum, and run with --silent as DECKY_USER.
        """
        async with self._lock:
            arch = os.uname().machine
            if arch != "x86_64":
                return {
                    "ok": False,
                    "error": "unsupported_arch",
                    "message": f"Unsupported CPU architecture: {arch}",
                }

            base_url = "https://github.com/rleeon/hoard/releases/latest/download"
            installer_name = f"HoardSetup-{arch}"
            installer_url = f"{base_url}/{installer_name}"
            checksum_url = f"{base_url}/{installer_name}.sha256"

            temp_dir = tempfile.mkdtemp(prefix="decky_hoard_install_")
            installer_path = os.path.join(temp_dir, "HoardSetup")
            try:
                logger.info(f"Downloading HoardSetup from {installer_url}...")
                req = urllib.request.Request(installer_url, headers={"User-Agent": "decky-hoard"})
                with urllib.request.urlopen(req, timeout=120) as resp, open(installer_path, "wb") as f:
                    shutil.copyfileobj(resp, f)

                # Fetch expected checksum
                expected_sha256 = None
                try:
                    chk_req = urllib.request.Request(checksum_url, headers={"User-Agent": "decky-hoard"})
                    with urllib.request.urlopen(chk_req, timeout=30) as resp:
                        chk_text = resp.read().decode("utf-8").strip()
                        expected_sha256 = chk_text.split()[0]
                except Exception as e:
                    logger.warning(f"Failed to fetch .sha256 checksum file: {e}")

                # Verify checksum if available
                if expected_sha256:
                    hasher = hashlib.sha256()
                    with open(installer_path, "rb") as f:
                        while chunk := f.read(65536):
                            hasher.update(chunk)
                    actual_sha256 = hasher.hexdigest()
                    if actual_sha256.lower() != expected_sha256.lower():
                        return {
                            "ok": False,
                            "error": "checksum_mismatch",
                            "message": f"SHA256 mismatch! Expected {expected_sha256}, got {actual_sha256}",
                        }
                    logger.info("HoardSetup checksum verified successfully.")

                # Make executable and transfer ownership
                os.chmod(installer_path, 0o755)
                if os.geteuid() == 0:
                    os.chown(installer_path, self._user_uid, self._user_gid)

                # Execute HoardSetup --silent
                env = _get_user_env(self._user_name, self._user_uid, self._user_home)
                cmd = [installer_path, "--silent"]
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

                logger.info("Executing HoardSetup --silent...")
                proc = await asyncio.create_subprocess_exec(*cmd, **kwargs)
                stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=300)
                stdout_str = stdout_b.decode("utf-8", errors="replace").strip()
                stderr_str = stderr_b.decode("utf-8", errors="replace").strip()

                if proc.returncode != 0:
                    logger.error(f"HoardSetup failed ({proc.returncode}): {stderr_str}")
                    return {
                        "ok": False,
                        "error": "setup_failed",
                        "message": f"HoardSetup failed with code {proc.returncode}: {stderr_str or stdout_str}",
                    }

                # Ensure permissions on binaries in ~/.local/bin
                local_bin = os.path.join(self._user_home, ".local", "bin")
                for bin_name in ["hoard", "hoardd"]:
                    bp = os.path.join(local_bin, bin_name)
                    if os.path.exists(bp):
                        os.chmod(bp, 0o755)
                        if os.geteuid() == 0:
                            os.chown(bp, self._user_uid, self._user_gid)

                if os.path.isfile(self._hoard_bin):
                    logger.info("Hoard successfully installed!")
                    return {"ok": True, "message": "Hoard installed successfully!"}
                else:
                    return {
                        "ok": False,
                        "error": "binary_missing",
                        "message": f"Installation finished but binary missing at {self._hoard_bin}",
                    }

            except Exception as e:
                logger.exception(f"Exception during Hoard installation: {e}")
                return {"ok": False, "error": "install_exception", "message": str(e)}
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

    async def force_sync(self) -> Dict[str, Any]:
        """
        Synchronize saves: start or restart the background sync daemon hoardd.
        """
        async with self._lock:
            status = await self.get_status()
            if not status.get("installed"):
                return {"ok": False, "message": "Hoard is not installed"}

            if not status.get("logged_in"):
                return {
                    "ok": False,
                    "message": "Not signed in to Hoard. Please run 'hoard login' in Desktop Mode.",
                }

            if status.get("service_running"):
                res = await self._run_hoard("sync", "restart", timeout=30)
                action = "restarted"
            else:
                res = await self._run_hoard("sync", "start", timeout=30)
                action = "started"

            if res["ok"]:
                return {
                    "ok": True,
                    "message": f"Hoard sync daemon {action} successfully! Syncing active.",
                }
            else:
                err_msg = res.get("stderr") or res.get("stdout") or "Unknown error"
                return {"ok": False, "message": f"Sync failed: {err_msg}"}

    async def track_game(self, game_name: str, slug: Optional[str] = None) -> Dict[str, Any]:
        """
        Track a game with Hoard CLI using exact slug if available, else fuzzy game name.
        """
        async with self._lock:
            if slug:
                args = ["track", "--slug", slug]
            else:
                args = ["track", game_name]

            logger.info(f"Tracking game with args: {args}")
            res = await self._run_hoard(*args, timeout=120)

            if res["ok"]:
                # Update cached game tracking state locally
                if self._cached_games:
                    norm_target = _normalize_name(slug or game_name)
                    for category in ["ready_to_track", "other_games"]:
                        for game in list(self._cached_games.get(category, [])):
                            game_norm = _normalize_name(game.get("slug") or game.get("name", ""))
                            if game_norm == norm_target or _normalize_name(game.get("name", "")) == _normalize_name(game_name):
                                game["tracked"] = True
                                self._cached_games[category].remove(game)
                                self._cached_games["tracked"].append(game)
                                break
                    # Update counts
                    self._update_cached_summary()

                return {
                    "ok": True,
                    "message": f"Game '{game_name}' is now being tracked by Hoard!",
                    "slug": slug,
                }
            else:
                err_msg = res.get("stderr") or res.get("stdout") or "Tracking failed"
                logger.warning(f"Track failed for {game_name}: {err_msg}")
                return {"ok": False, "message": f"Could not track '{game_name}': {err_msg}"}

    def _update_cached_summary(self):
        if not self._cached_games:
            return
        ready = len(self._cached_games.get("ready_to_track", []))
        other = len(self._cached_games.get("other_games", []))
        tracked = len(self._cached_games.get("tracked", []))
        missing = len(self._cached_games.get("missing_folder", []))
        self._cached_games["summary"] = {
            "total": ready + other + tracked + missing,
            "ready_count": ready,
            "other_count": other,
            "tracked_count": tracked,
            "missing_count": missing,
        }

    def _find_steam_libraries(self) -> List[str]:
        """Locate all Steam library folders (SSD + SD cards)."""
        candidate_roots = [
            os.path.join(self._user_home, ".local", "share", "Steam"),
            os.path.join(self._user_home, ".steam", "steam"),
            os.path.join(self._user_home, ".steam", "root"),
            os.path.join(
                self._user_home,
                ".var",
                "app",
                "com.valvesoftware.Steam",
                ".local",
                "share",
                "Steam",
            ),
        ]

        found_libraries: set = set()
        for root in candidate_roots:
            if not os.path.isdir(root):
                continue
            resolved = os.path.realpath(root)
            found_libraries.add(resolved)

            vdf_path = os.path.join(resolved, "steamapps", "libraryfolders.vdf")
            if os.path.isfile(vdf_path):
                try:
                    with open(vdf_path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    # Extract "path" "/mount/point"
                    matches = re.findall(r'"path"\s+"([^"]+)"', content)
                    for path in matches:
                        if os.path.isdir(path):
                            found_libraries.add(os.path.realpath(path))
                except Exception as e:
                    logger.warning(f"Error reading {vdf_path}: {e}")

        return list(found_libraries)

    def _scan_steam_installed_games(self) -> List[Dict[str, Any]]:
        """Parse appmanifest_*.acf files across all discovered Steam libraries."""
        libraries = self._find_steam_libraries()
        games: List[Dict[str, Any]] = []
        seen_appids: set = set()

        for lib in libraries:
            steamapps = os.path.join(lib, "steamapps")
            if not os.path.isdir(steamapps):
                continue

            try:
                for entry in os.scandir(steamapps):
                    if not (entry.is_file() and entry.name.startswith("appmanifest_") and entry.name.endswith(".acf")):
                        continue

                    try:
                        with open(entry.path, "r", encoding="utf-8", errors="replace") as f:
                            text = f.read()

                        # Parse appid and name
                        appid_match = re.search(r'"appid"\s+"([^"]+)"', text)
                        name_match = re.search(r'"name"\s+"([^"]+)"', text)
                        if not appid_match or not name_match:
                            continue

                        appid = appid_match.group(1).strip()
                        name = name_match.group(1).strip()

                        if appid in seen_appids or appid in EXCLUDED_APPIDS:
                            continue

                        # Check name patterns
                        if any(pattern.search(name) for pattern in EXCLUDED_NAME_PATTERNS):
                            continue

                        seen_appids.add(appid)
                        games.append({
                            "appid": appid,
                            "name": name,
                            "library": lib,
                        })
                    except Exception as e:
                        logger.debug(f"Error parsing {entry.name}: {e}")
            except Exception as e:
                logger.warning(f"Error scanning steamapps in {lib}: {e}")

        games.sort(key=lambda g: g["name"].lower())
        return games

    async def get_games(self, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Hybrid game discovery:
        1. Parse local Steam VDF/ACF manifests (installed Steam games).
        2. Query `hoard scan --json` (detected save locations, slugs, confidence, needs_folder).
        3. Query `hoard saves --json` (already tracked saves).
        4. Match and categorize into 4 ordered groups:
           - ready_to_track
           - other_games
           - tracked
           - missing_folder
        """
        if self._cached_games and not force_refresh:
            return self._cached_games

        self._is_scanning = True
        try:
            # 1. Parse Steam manifests
            steam_games = self._scan_steam_installed_games()

            # 2. Query hoard saves (tracked saves)
            tracked_slugs: set = set()
            tracked_names: set = set()
            saves_res = await self._run_hoard("saves", "--json", timeout=20)
            if saves_res["ok"] and saves_res.get("data"):
                saves_list = saves_res["data"].get("data", {}).get("saves", [])
                for s in saves_list:
                    if s.get("slug"):
                        tracked_slugs.add(s["slug"].lower())
                    if s.get("game_name"):
                        tracked_names.add(_normalize_name(s["game_name"]))

            # 3. Query hoard scan --json
            scan_games_map: Dict[str, Dict[str, Any]] = {}
            scan_res = await self._run_hoard("scan", "--json", timeout=180)
            if scan_res["ok"] and scan_res.get("data"):
                scanned_list = scan_res["data"].get("data", {}).get("games", [])
                for sg in scanned_list:
                    slug = sg.get("slug", "")
                    disp_name = sg.get("display_name", "")
                    norm = _normalize_name(disp_name or slug)
                    scan_games_map[norm] = sg
                    if slug:
                        scan_games_map[slug.lower()] = sg

            ready_to_track: List[Dict[str, Any]] = []
            other_games: List[Dict[str, Any]] = []
            tracked: List[Dict[str, Any]] = []
            missing_folder: List[Dict[str, Any]] = []

            seen_tracked_slugs: set = set()

            for sg in steam_games:
                name = sg["name"]
                appid = sg["appid"]
                norm = _normalize_name(name)

                # Match with scan entry
                scan_entry = scan_games_map.get(norm)

                is_tracked = False
                slug = None
                needs_folder = False
                paths = []

                if scan_entry:
                    slug = scan_entry.get("slug")
                    is_tracked = bool(scan_entry.get("tracked"))
                    needs_folder = bool(scan_entry.get("needs_folder"))
                    paths = scan_entry.get("paths", [])

                if not is_tracked:
                    if (slug and slug.lower() in tracked_slugs) or norm in tracked_names:
                        is_tracked = True

                item = {
                    "name": name,
                    "appid": appid,
                    "slug": slug,
                    "needs_folder": needs_folder,
                    "paths": paths,
                    "tracked": is_tracked,
                }

                if slug:
                    seen_tracked_slugs.add(slug.lower())

                if is_tracked:
                    tracked.append(item)
                elif needs_folder:
                    missing_folder.append(item)
                elif scan_entry:
                    ready_to_track.append(item)
                else:
                    other_games.append(item)

            # Include any scanned games that are already tracked but weren't in Steam manifests (e.g. GOG, Epic, emulators)
            for norm, sg in scan_games_map.items():
                slug = sg.get("slug")
                if not slug or slug.lower() in seen_tracked_slugs:
                    continue
                is_tracked = bool(sg.get("tracked")) or (slug.lower() in tracked_slugs)
                if is_tracked:
                    seen_tracked_slugs.add(slug.lower())
                    tracked.append({
                        "name": sg.get("display_name", slug),
                        "appid": None,
                        "slug": slug,
                        "needs_folder": bool(sg.get("needs_folder")),
                        "paths": sg.get("paths", []),
                        "tracked": True,
                    })

            # Sort alphabetically within each category
            ready_to_track.sort(key=lambda x: x["name"].lower())
            other_games.sort(key=lambda x: x["name"].lower())
            tracked.sort(key=lambda x: x["name"].lower())
            missing_folder.sort(key=lambda x: x["name"].lower())

            result = {
                "ready_to_track": ready_to_track,
                "other_games": other_games,
                "tracked": tracked,
                "missing_folder": missing_folder,
                "summary": {
                    "total": len(ready_to_track) + len(other_games) + len(tracked) + len(missing_folder),
                    "ready_count": len(ready_to_track),
                    "other_count": len(other_games),
                    "tracked_count": len(tracked),
                    "missing_count": len(missing_folder),
                },
            }

            self._cached_games = result
            return result
        finally:
            self._is_scanning = False
