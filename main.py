import asyncio
import hashlib
import json
import logging
import os
import pwd
import re
import shlex
import shutil
import tempfile
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

# Attempt import of decky (available when running inside Decky Loader)
try:
    import decky
except ImportError:
    decky = None

if decky and hasattr(decky, "logger"):
    logger = decky.logger
else:
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

    if not user_name or user_name == "root":
        user_name = os.environ.get("DECKY_USER") or os.environ.get("SUDO_USER")

    # Extract username from plugin path (/home/<user>/... or /var/home/<user>/...)
    if not user_name or user_name == "root":
        abs_path = os.path.abspath(__file__)
        m = re.match(r"^/var/home/([^/]+)|^/home/([^/]+)", abs_path)
        if m:
            candidate = m.group(1) or m.group(2)
            try:
                entry = pwd.getpwnam(candidate)
                if entry.pw_uid >= 1000:
                    user_name = entry.pw_name
                    user_home = entry.pw_dir
            except KeyError:
                pass

    # If still root or unset, look for 'deck' user or first UID >= 1000 with a home dir
    if not user_name or user_name == "root":
        try:
            deck_entry = pwd.getpwnam("deck")
            user_name = deck_entry.pw_name
            user_home = deck_entry.pw_dir
        except KeyError:
            for entry in pwd.getpwall():
                if entry.pw_uid >= 1000 and os.path.exists(entry.pw_dir) and "home" in entry.pw_dir:
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
    if not user_home or user_home == "/root":
        user_home = entry.pw_dir

    return user_name, user_uid, user_gid, user_home


def _get_user_env(user_name: str, user_uid: int, user_home: str) -> Dict[str, str]:
    """Prepare environment variables needed by Hoard and systemd --user."""
    runtime_dir = f"/run/user/{user_uid}"
    bus_path = f"unix:path={runtime_dir}/bus"
    real_home = os.path.realpath(user_home)

    env = dict(os.environ)
    env["USER"] = user_name
    env["LOGNAME"] = user_name
    env["HOME"] = user_home
    env["SHELL"] = "/bin/bash"
    env["XDG_CONFIG_HOME"] = os.path.join(user_home, ".config")
    env["XDG_DATA_HOME"] = os.path.join(user_home, ".local", "share")
    env["XDG_STATE_HOME"] = os.path.join(user_home, ".local", "state")
    env["XDG_CACHE_HOME"] = os.path.join(user_home, ".cache")
    env["XDG_RUNTIME_DIR"] = runtime_dir
    env["DBUS_SESSION_BUS_ADDRESS"] = bus_path
    bin_path = f"{user_home}/.local/bin:{real_home}/.local/bin"
    env["PATH"] = f"{bin_path}:/usr/local/bin:/usr/bin:/bin:{env.get('PATH', '')}"
    return env


class HoardBackend:
    """
    Actual stateful backend instance.
    Decky Loader calls methods on the `Plugin` class directly without calling `Plugin.__init__()`,
    so delegating to a singleton `HoardBackend` instance ensures state and bound methods work properly.
    """

    def __init__(self):
        self._lock: Optional[asyncio.Lock] = None
        self._scan_lock: Optional[asyncio.Lock] = None
        self._user_name, self._user_uid, self._user_gid, self._user_home = _get_decky_user_info()
        self._hoard_bin = os.path.join(self._user_home, ".local", "bin", "hoard")
        self._cached_games: Optional[Dict[str, Any]] = None
        self._is_scanning = False
        logger.info(
            f"Initialized HoardBackend for user={self._user_name} (uid={self._user_uid}, home={self._user_home}), bin={self._hoard_bin}"
        )

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
        found = shutil.which("hoard", path=env.get("PATH"))
        if found:
            self._hoard_bin = found
        return self._hoard_bin

    def _has_local_session_config(self) -> bool:
        """
        Check if Hoard has local configuration / credentials / token files in the user's home directory.
        """
        candidate_dirs = [
            os.path.join(self._user_home, ".config", "hoard"),
            os.path.join(self._user_home, ".local", "share", "hoard"),
            os.path.join(self._user_home, ".hoard"),
        ]
        auth_keywords = ("token", "session", "auth", "credential", "api_key", "server", "user", "email")

        for d in candidate_dirs:
            if not os.path.isdir(d):
                continue
            try:
                for root, _, files in os.walk(d):
                    for fname in files:
                        fpath = os.path.join(root, fname)
                        lower_name = fname.lower()
                        if lower_name in ("credentials", "credentials.json", "credentials.toml", "session.json", "auth.json", "token"):
                            if os.path.getsize(fpath) > 0:
                                return True
                        if lower_name.endswith((".toml", ".json", ".yaml", ".yml", ".conf")):
                            try:
                                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                                    content = f.read(16384).lower()
                                if any(k in content for k in auth_keywords):
                                    return True
                            except Exception:
                                pass
            except Exception:
                pass
        return False

    async def _run_hoard(self, *args: str, timeout: int = 60) -> Dict[str, Any]:
        """
        Execute `hoard <args>` via `/bin/bash -lc` as DECKY_USER with standard environment.
        """
        hoard_cmd = shlex.join(["hoard", *args])
        cmd = ["/bin/bash", "-lc", hoard_cmd]
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
            stdout_str = stdout_b.decode("utf-8", errors="replace").strip()
            stderr_str = stderr_b.decode("utf-8", errors="replace").strip()
            rc = proc.returncode

            if rc == 127:
                return {
                    "ok": False,
                    "returncode": rc,
                    "error": "not_installed",
                    "stdout": stdout_str,
                    "stderr": stderr_str,
                    "message": "Hoard command not found in /bin/bash PATH",
                }

            data = None
            if stdout_str:
                try:
                    data = json.loads(stdout_str)
                except Exception:
                    brace_idx = stdout_str.find("{")
                    if brace_idx != -1:
                        try:
                            data = json.loads(stdout_str[brace_idx:])
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
            logger.error(f"Command timed out ({timeout}s): {hoard_cmd}")
            return {
                "ok": False,
                "returncode": -2,
                "error": "timeout",
                "message": f"Command timed out after {timeout} seconds",
            }
        except Exception as e:
            logger.exception(f"Error running Hoard command {hoard_cmd}: {e}")
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
        hoard_bin = self._resolve_hoard_bin()
        installed = os.path.isfile(hoard_bin) and os.access(hoard_bin, os.X_OK)

        # 1. Check version via /bin/bash -lc "hoard --version"
        version_res = await self._run_hoard("--version", timeout=10)
        if version_res["ok"]:
            installed = True
        if not installed:
            return {
                "installed": False,
                "version": None,
                "logged_in": False,
                "user_info": None,
                "service_running": False,
                "is_scanning": self._is_scanning,
                "binary_path": hoard_bin,
            }

        version = version_res.get("stdout") if version_res["ok"] else "Installed"

        # 2. Check sync service via /bin/bash -lc "systemctl --user is-active hoard-sync.service"
        service_running = False
        try:
            env = _get_user_env(self._user_name, self._user_uid, self._user_home)
            cmd = ["/bin/bash", "-lc", "systemctl --user is-active hoard-sync.service"]
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

        sync_res = await self._run_hoard("sync", timeout=8)
        stdout_sync = (sync_res.get("stdout") or "").lower()
        stderr_sync = (sync_res.get("stderr") or "").lower()
        if not service_running:
            service_running = (
                ("running" in stdout_sync and "not running" not in stdout_sync)
                or ("active" in stdout_sync and "inactive" not in stdout_sync)
            )

        # 3. Check session / login state using multiple signals
        logged_in = False
        user_info = None
        not_logged_phrases = (
            "not logged in",
            "no session",
            "no_session",
            "not authenticated",
            "unauthenticated",
            "please login",
            "please log in",
            "run 'hoard login'",
            "run `hoard login`",
        )
        cli_error_phrases = (
            "unexpected argument",
            "unrecognized subcommand",
            "invalid subcommand",
            "unknown option",
            "found argument",
        )

        # Signal A: Try `hoard whoami --json` then `hoard whoami`
        whoami_res = await self._run_hoard("whoami", "--json", timeout=10)
        combined_whoami = f"{whoami_res.get('stdout') or ''}\n{whoami_res.get('stderr') or ''}".lower()
        if not whoami_res["ok"] and any(p in combined_whoami for p in cli_error_phrases):
            whoami_res = await self._run_hoard("whoami", timeout=10)
            combined_whoami = f"{whoami_res.get('stdout') or ''}\n{whoami_res.get('stderr') or ''}".lower()

        explicitly_logged_out = False
        if any(p in combined_whoami for p in not_logged_phrases):
            explicitly_logged_out = True
        elif isinstance(whoami_res.get("data"), dict):
            raw_data = whoami_res["data"]
            err_val = str(raw_data.get("error") or "").lower()
            msg_val = str(raw_data.get("message") or "").lower()
            if any(p in err_val or p in msg_val for p in not_logged_phrases):
                explicitly_logged_out = True
            elif raw_data.get("ok") is not False:
                logged_in = True
                user_info = raw_data.get("data", raw_data)
        elif whoami_res["ok"]:
            logged_in = True
            user_info = {"user": whoami_res.get("stdout")}

        # Signal B: If sync daemon is active, or `hoard sync` succeeded without a login error, or local session config exists
        if not logged_in and not explicitly_logged_out:
            combined_sync = f"{stdout_sync}\n{stderr_sync}"
            if service_running:
                logged_in = True
            elif sync_res["ok"] and not any(p in combined_sync for p in not_logged_phrases):
                logged_in = True
            elif self._has_local_session_config():
                logged_in = True

        # Signal C: Even if whoami failed (e.g. offline or self-hosted server), if local config + daemon are active, consider logged in
        if not logged_in and (service_running or self._has_local_session_config()):
            logged_in = True

        logger.info(
            f"Status check: installed={installed}, logged_in={logged_in}, service_running={service_running}"
        )

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
        """
        Download HoardSetup-x86_64, verify SHA256 checksum, and run with --silent as DECKY_USER.
        """
        async with self.lock:
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
                def _download_and_verify() -> Optional[Dict[str, Any]]:
                    logger.info(f"Downloading HoardSetup from {installer_url}...")
                    req = urllib.request.Request(installer_url, headers={"User-Agent": "decky-hoard"})
                    with urllib.request.urlopen(req, timeout=120) as resp, open(installer_path, "wb") as f:
                        shutil.copyfileobj(resp, f)

                    expected_sha256 = None
                    try:
                        chk_req = urllib.request.Request(checksum_url, headers={"User-Agent": "decky-hoard"})
                        with urllib.request.urlopen(chk_req, timeout=30) as resp:
                            chk_text = resp.read().decode("utf-8").strip()
                            expected_sha256 = chk_text.split()[0]
                    except Exception as e:
                        logger.warning(f"Failed to fetch .sha256 checksum file: {e}")

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
                    return None

                verify_err = await asyncio.to_thread(_download_and_verify)
                if verify_err:
                    return verify_err

                os.chmod(installer_path, 0o755)
                if os.geteuid() == 0:
                    os.chown(installer_path, self._user_uid, self._user_gid)

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

                local_bin = os.path.join(self._user_home, ".local", "bin")
                for bin_name in ["hoard", "hoardd"]:
                    bp = os.path.join(local_bin, bin_name)
                    if os.path.exists(bp):
                        os.chmod(bp, 0o755)
                        if os.geteuid() == 0:
                            os.chown(bp, self._user_uid, self._user_gid)

                hoard_bin = self._resolve_hoard_bin()
                if os.path.isfile(hoard_bin):
                    logger.info("Hoard successfully installed!")
                    return {"ok": True, "message": "Hoard installed successfully!"}
                else:
                    return {
                        "ok": False,
                        "error": "binary_missing",
                        "message": f"Installation finished but binary missing at {hoard_bin}",
                    }

            except Exception as e:
                logger.exception(f"Exception during Hoard installation: {e}")
                return {"ok": False, "error": "install_exception", "message": str(e)}
            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

    async def _get_tracked_saves_list(self) -> List[Dict[str, Any]]:
        """
        Query `hoard saves --json` and return the list of tracked save entries.
        Each entry typically contains `save_id`, `game_slug`, `label`, `local_path`, etc.
        """
        saves_res = await self._run_hoard("saves", "--json", timeout=20)
        if not (saves_res["ok"] and saves_res.get("data")):
            return []

        raw_saves = saves_res["data"]
        if isinstance(raw_saves, dict):
            inner = raw_saves.get("data", raw_saves)
            saves_list = (
                inner.get("saves", [])
                if isinstance(inner, dict)
                else (inner if isinstance(inner, list) else [])
            )
        elif isinstance(raw_saves, list):
            saves_list = raw_saves
        else:
            saves_list = []

        return [s for s in saves_list if isinstance(s, dict)]

    async def force_sync(self) -> Dict[str, Any]:
        """
        Synchronize saves: start or restart the background sync daemon hoardd,
        and run `hoard backup <save_id>` for all tracked saves so changes are
        immediately uploaded to the cloud/server.
        """
        async with self.lock:
            status = await self.get_status()
            if not status.get("installed"):
                return {"ok": False, "message": "Hoard is not installed"}

            if status.get("service_running"):
                res = await self._run_hoard("sync", "restart", timeout=30)
                action = "restarted"
            else:
                res = await self._run_hoard("sync", "start", timeout=30)
                action = "started"

            # Upload all tracked saves immediately
            saves_list = await self._get_tracked_saves_list()
            backed_up = 0
            backup_errors: List[str] = []
            for s in saves_list:
                save_id = s.get("save_id")
                if not save_id or s.get("paused"):
                    continue
                b_res = await self._run_hoard("backup", str(save_id), timeout=180)
                if b_res["ok"]:
                    backed_up += 1
                else:
                    err = b_res.get("stderr") or b_res.get("stdout") or "Backup error"
                    logger.warning(f"Backup failed for save_id={save_id}: {err}")
                    backup_errors.append(err)

            if res["ok"] or backed_up > 0:
                return {
                    "ok": True,
                    "message": f"Hoard sync daemon {action} ({backed_up} save(s) backed up).",
                }
            else:
                err_msg = (
                    (backup_errors[0] if backup_errors else None)
                    or res.get("stderr")
                    or res.get("stdout")
                    or "Unknown error"
                )
                return {"ok": False, "message": f"Sync failed: {err_msg}"}

    async def track_game(self, game_name: str, slug: Optional[str] = None) -> Dict[str, Any]:
        """
        Track a game with Hoard CLI (`hoard track <game_name>`, with fallback to `--slug`),
        then immediately trigger `hoard backup <save_id>` so the save is uploaded to the cloud.
        """
        async with self.lock:
            args = ["track", game_name]
            logger.info(f"Tracking game with args: {args}")
            res = await self._run_hoard(*args, timeout=120)

            if not res["ok"] and slug:
                fallback_args = ["track", "--slug", slug]
                logger.info(f"Fallback tracking game with args: {fallback_args}")
                res = await self._run_hoard(*fallback_args, timeout=120)

            if res["ok"]:
                stdout_text = res.get("stdout") or ""

                # Extract resolved slug and save_id from `hoard track` output if present:
                #   tracking <display_name> (<slug>)
                #     path:    <path>
                #     save_id: <uuid>
                resolved_slug = slug
                slug_match = re.search(r"^tracking\s+.+\(([^)]+)\)", stdout_text, re.MULTILINE)
                if slug_match:
                    resolved_slug = slug_match.group(1).strip()

                save_id: Optional[str] = None
                save_id_match = re.search(r"save_id:\s*([0-9a-fA-F-]{36}|\S+)", stdout_text)
                if save_id_match:
                    save_id = save_id_match.group(1).strip()

                # Fallback: look up save_id via `hoard saves --json`
                if not save_id:
                    saves_list = await self._get_tracked_saves_list()
                    target_norms = {
                        _normalize_name(game_name),
                        _normalize_name(resolved_slug or ""),
                        _normalize_name(slug or ""),
                    } - {""}
                    for s in saves_list:
                        s_slug = str(s.get("game_slug") or s.get("slug") or "")
                        if _normalize_name(s_slug) in target_norms:
                            save_id = str(s.get("save_id") or "") or None
                            if not resolved_slug and s_slug:
                                resolved_slug = s_slug
                            break

                # Immediately upload the first snapshot to Cloud / Server
                if save_id:
                    logger.info(f"Uploading initial backup for '{game_name}' (save_id={save_id})...")
                    backup_res = await self._run_hoard("backup", save_id, timeout=180)
                    if not backup_res["ok"]:
                        b_err = backup_res.get("stderr") or backup_res.get("stdout") or "Unknown backup error"
                        logger.warning(f"Initial backup failed for {game_name} ({save_id}): {b_err}")

                if self._cached_games:
                    norm_target = _normalize_name(resolved_slug or slug or game_name)
                    for category in ["ready_to_track", "other_games"]:
                        for game in list(self._cached_games.get(category, [])):
                            game_norm = _normalize_name(game.get("slug") or game.get("name", ""))
                            if game_norm == norm_target or _normalize_name(game.get("name", "")) == _normalize_name(game_name):
                                game["tracked"] = True
                                if resolved_slug and not game.get("slug"):
                                    game["slug"] = resolved_slug
                                self._cached_games[category].remove(game)
                                self._cached_games["tracked"].append(game)
                                break
                    self._update_cached_summary()

                return {
                    "ok": True,
                    "message": f"Game '{game_name}' is now being tracked by Hoard!",
                    "slug": resolved_slug,
                    "save_id": save_id,
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

                        appid_match = re.search(r'"appid"\s+"([^"]+)"', text)
                        name_match = re.search(r'"name"\s+"([^"]+)"', text)
                        if not appid_match or not name_match:
                            continue

                        appid = appid_match.group(1).strip()
                        name = name_match.group(1).strip()

                        if appid in seen_appids or appid in EXCLUDED_APPIDS:
                            continue

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
        async with self.scan_lock:
            if self._cached_games and not force_refresh:
                return self._cached_games

            self._is_scanning = True
            try:
                # 1. Parse Steam manifests
                steam_games = self._scan_steam_installed_games()

                # 2. Query hoard saves (tracked saves)
                tracked_slugs: set = set()
                tracked_names: set = set()
                tracked_paths: set = set()
                saves_list = await self._get_tracked_saves_list()
                for s in saves_list:
                    g_slug = str(s.get("game_slug") or s.get("slug") or "").strip()
                    if g_slug:
                        tracked_slugs.add(g_slug.lower())
                        tracked_names.add(_normalize_name(g_slug))
                    g_name = str(s.get("game_name") or "").strip()
                    if g_name:
                        tracked_names.add(_normalize_name(g_name))
                    l_path = str(s.get("local_path") or "").strip()
                    if l_path:
                        tracked_paths.add(l_path)

                # 3. Query hoard scan --json
                scan_games_map: Dict[str, Dict[str, Any]] = {}
                scanned_entries: List[Dict[str, Any]] = []
                scan_res = await self._run_hoard("scan", "--json", timeout=180)
                if scan_res["ok"] and scan_res.get("data"):
                    raw_scan = scan_res["data"]
                    if isinstance(raw_scan, dict):
                        inner = raw_scan.get("data", raw_scan)
                        scanned_list = inner.get("games", []) if isinstance(inner, dict) else (inner if isinstance(inner, list) else [])
                    elif isinstance(raw_scan, list):
                        scanned_list = raw_scan
                    else:
                        scanned_list = []

                    for sg in scanned_list:
                        if isinstance(sg, dict):
                            scanned_entries.append(sg)
                            slug = sg.get("slug", "")
                            disp_name = sg.get("display_name", "")
                            norm_disp = _normalize_name(disp_name)
                            norm_slug = _normalize_name(slug)
                            if norm_disp:
                                scan_games_map[norm_disp] = sg
                            if norm_slug:
                                scan_games_map[norm_slug] = sg
                            if slug:
                                scan_games_map[slug.lower()] = sg

                ready_to_track: List[Dict[str, Any]] = []
                other_games: List[Dict[str, Any]] = []
                tracked: List[Dict[str, Any]] = []
                missing_folder: List[Dict[str, Any]] = []

                seen_scan_slugs: set = set()

                for sg in steam_games:
                    name = sg["name"]
                    appid = sg["appid"]
                    norm = _normalize_name(name)

                    scan_entry = scan_games_map.get(norm)
                    if not scan_entry and len(norm) >= 5:
                        # Fallback match when Steam adds edition suffixes or punctuation differences
                        candidates = [
                            entry
                            for entry in scanned_entries
                            if entry.get("slug", "").lower() not in seen_scan_slugs
                            and (
                                norm in _normalize_name(entry.get("display_name", ""))
                                or _normalize_name(entry.get("display_name", "")) in norm
                            )
                            and len(_normalize_name(entry.get("display_name", ""))) >= 5
                        ]
                        if len(candidates) == 1:
                            scan_entry = candidates[0]

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
                        if (
                            (slug and slug.lower() in tracked_slugs)
                            or norm in tracked_names
                            or any(p in tracked_paths for p in paths)
                        ):
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
                        seen_scan_slugs.add(slug.lower())

                    if is_tracked:
                        tracked.append(item)
                    elif needs_folder:
                        missing_folder.append(item)
                    elif scan_entry:
                        ready_to_track.append(item)
                    else:
                        other_games.append(item)

                # Include any remaining scanned games from `hoard scan --json` (tracked, ready, or missing folder)
                for sg in scanned_entries:
                    slug = sg.get("slug")
                    if not slug or slug.lower() in seen_scan_slugs:
                        continue
                    seen_scan_slugs.add(slug.lower())

                    disp_name = sg.get("display_name") or slug
                    paths = sg.get("paths", [])
                    needs_folder = bool(sg.get("needs_folder"))
                    is_tracked = (
                        bool(sg.get("tracked"))
                        or (slug.lower() in tracked_slugs)
                        or (_normalize_name(disp_name) in tracked_names)
                        or any(p in tracked_paths for p in paths)
                    )

                    item = {
                        "name": disp_name,
                        "appid": None,
                        "slug": slug,
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

                # Include any tracked saves from `hoard saves --json` not yet represented
                for s in saves_list:
                    g_slug = str(s.get("game_slug") or s.get("slug") or "").strip()
                    if not g_slug or g_slug.lower() in seen_scan_slugs:
                        continue
                    seen_scan_slugs.add(g_slug.lower())
                    l_path = str(s.get("local_path") or "").strip()
                    tracked.append({
                        "name": str(s.get("game_name") or g_slug),
                        "appid": None,
                        "slug": g_slug,
                        "needs_folder": False,
                        "paths": [l_path] if l_path else [],
                        "tracked": True,
                    })

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


_backend: Optional[HoardBackend] = None


def _get_backend() -> HoardBackend:
    global _backend
    if _backend is None:
        _backend = HoardBackend()
    return _backend


class Plugin:
    async def _main(self):
        logger.info("Hoard plugin loaded.")
        backend = _get_backend()
        asyncio.create_task(backend.get_games(force_refresh=False))

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

    async def get_games(self, force_refresh: bool = False) -> Dict[str, Any]:
        return await _get_backend().get_games(force_refresh)
