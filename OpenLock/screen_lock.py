"""
screen_lock.py
--------------
Cooperative screen-time / app-blocking tool for Windows 11.

Reads a config.json file specifying:
  - a list of blocked apps (full .exe path OR just the executable name)
  - a daily time window during which those apps should be blocked
  - how often (in seconds) to check for violations

While running, it loops forever: if the current time falls inside the
blocked window, it scans all running processes and terminates any
process whose name or full path matches an entry in blocked_apps.

This is a *cooperative* tool: it does not attempt to hide itself,
prevent itself from being killed, or survive Safe Mode. It's meant for
self-imposed limits, not for blocking a determined adversary.
"""

import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

import psutil

CONFIG_PATH = Path(__file__).parent / "config.json"
LOG_PATH = Path(__file__).parent / "screen_lock.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("screen_lock")


def load_config(path: Path) -> dict:
    """Load and lightly validate the config file."""
    if not path.exists():
        log.error("Config file not found at %s", path)
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        config = json.load(f)

    required_keys = {"blocked_apps", "start_time", "end_time"}
    missing = required_keys - config.keys()
    if missing:
        log.error("Config is missing required keys: %s", missing)
        sys.exit(1)

    config.setdefault("check_interval_seconds", 5)
    return config


def parse_time_str(time_str: str) -> tuple[int, int]:
    """Parse 'HH:MM' into (hour, minute)."""
    try:
        hour, minute = map(int, time_str.split(":"))
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError
        return hour, minute
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"Invalid time format: '{time_str}'. Use 'HH:MM' (24h).") from exc


def is_within_blocked_window(start_time: str, end_time: str) -> bool:
    """
    Return True if the current local time falls within [start_time, end_time).
    Supports windows that cross midnight (e.g. start=22:00, end=06:00).
    """
    now_dt = datetime.now()
    now = now_dt.time()
    start_h, start_m = parse_time_str(start_time)
    end_h, end_m = parse_time_str(end_time)

    start = now_dt.replace(hour=start_h, minute=start_m, second=0, microsecond=0).time()
    end = now_dt.replace(hour=end_h, minute=end_m, second=0, microsecond=0).time()

    if start <= end:
        # Normal same-day window, e.g. 09:00 - 17:00
        return start <= now <= end
    else:
        # Window crosses midnight, e.g. 22:00 - 06:00
        return now >= start or now <= end


def normalize(s: str) -> str:
    return s.strip().lower()


def matches_blocklist(proc: psutil.Process, blocked_apps: list[str]) -> bool:
    """
    Check whether a running process matches any entry in blocked_apps.
    Entries can be a full path or just an executable name.
    """
    try:
        proc_name = normalize(proc.name())  # e.g. "steam.exe"
        proc_path = proc.exe()  # full path; may raise AccessDenied
        proc_path_norm = normalize(proc_path) if proc_path else ""
    except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
        return False

    for entry in blocked_apps:
        entry_norm = normalize(entry)
        # Treat as a full path if it contains a path separator of either
        # style, or a drive letter (e.g. "C:\..."). This check is
        # OS-independent so it works correctly on Windows regardless of
        # how the path string was typed.
        is_path = "\\" in entry_norm or "/" in entry_norm or ":" in entry_norm

        if is_path:
            if proc_path_norm == entry_norm:
                return True
        else:
            if proc_name == entry_norm:
                return True
    return False


def enforce_blocklist(blocked_apps: list[str]) -> None:
    """Scan all running processes and kill any that match the blocklist."""
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if matches_blocklist(proc, blocked_apps):
                log.info("Blocking '%s' (PID %s)", proc.name(), proc.pid)
                proc.kill()
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
            # Process may have already exited, or we lack permission
            # (e.g. some system processes). Safe to skip.
            continue


def main() -> None:
    log.info("screen_lock started. Reading config from %s", CONFIG_PATH)

    last_config_mtime = None
    config = None

    while True:
        try:
            # Reload config if it changed on disk, so edits take effect
            # without restarting the script.
            mtime = CONFIG_PATH.stat().st_mtime
            if mtime != last_config_mtime:
                config = load_config(CONFIG_PATH)
                last_config_mtime = mtime
                log.info(
                    "Config (re)loaded: %d blocked app(s), window %s-%s",
                    len(config["blocked_apps"]),
                    config["start_time"],
                    config["end_time"],
                )

            if is_within_blocked_window(config["start_time"], config["end_time"]):
                enforce_blocklist(config["blocked_apps"])

            time.sleep(config["check_interval_seconds"])

        except KeyboardInterrupt:
            log.info("screen_lock stopped by user.")
            break
        except Exception:
            # Don't let one bad cycle crash the whole loop; log and continue.
            log.exception("Unexpected error in main loop; continuing.")
            time.sleep(5)


if __name__ == "__main__":
    main()
