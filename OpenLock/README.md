# Screen Time Lock

A simple, cooperative app-blocking tool for Windows 11. It blocks a list of
programs you choose, during a time window you choose, and can start
automatically when you log in.

**This is for self-imposed limits, not for blocking a determined adversary.**
Anyone with admin access (likely you) can stop the script, end the
scheduled task, or edit the config — there's no anti-tamper protection.
It works because you've agreed to the rules, not because it's unbreakable.

## Files

- `screen_lock.py` — the script that does the blocking
- `config.json` — your list of blocked apps + the time window
- `setup_autostart.ps1` — one-time setup to run it automatically at login
- `screen_lock.log` — created automatically; shows what got blocked and when

## Requirements

- Python 3.10+ installed on Windows, with the `psutil` package:
  ```
  pip install psutil
  ```

## 1. Configure what to block

Open `config.json` in any text editor. Example:

```json
{
  "blocked_apps": [
    "steam.exe",
    "C:\\Users\\YourName\\AppData\\Local\\Discord\\Discord.exe"
  ],
  "start_time": "09:00",
  "end_time": "17:00",
  "check_interval_seconds": 5
}
```

- **blocked_apps**: each entry is either:
  - just the executable name (e.g. `"steam.exe"`) — blocks it no matter
    where it's installed, or
  - a full path (e.g. `"C:\\Program Files\\App\\app.exe"`) — blocks only
    that specific install.

  To find an app's exe name or path: open Task Manager → right-click the
  running app → "Open file location". The address bar shows the full path.

- **start_time / end_time**: 24-hour `HH:MM` format. The window can cross
  midnight (e.g. `"22:00"` to `"06:00"` blocks overnight).

- **check_interval_seconds**: how often (in seconds) it checks for
  blocked apps and the current time. Lower = more responsive, slightly
  more CPU use. 5 seconds is a sensible default.

You can edit `config.json` and save it any time — the running script
picks up changes automatically within one check interval, no restart needed.

## 2. Test it manually first

Before setting up auto-start, run it directly to make sure it behaves as
expected:

```
python screen_lock.py
```

Try opening a blocked app during the blocked window — it should close
within `check_interval_seconds`. Check `screen_lock.log` to see what
happened. Press `Ctrl+C` to stop.

## 3. Set up auto-start at login

1. Right-click `setup_autostart.ps1` → "Run with PowerShell"
   (or open PowerShell **as Administrator**, `cd` to this folder, and run
   `.\setup_autostart.ps1`).
   - If PowerShell blocks the script with an "execution policy" error, run
     this first in an admin PowerShell window:
     ```
     Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
     ```
2. This registers a Task Scheduler task named **ScreenTimeLock** that
   starts the script automatically every time you log in, runs it
   silently in the background (no console window), and restarts it if it
   crashes.
3. To start it immediately without rebooting:
   ```
   Start-ScheduledTask -TaskName "ScreenTimeLock"
   ```

## Removing it

To stop auto-start entirely:
```
Unregister-ScheduledTask -TaskName "ScreenTimeLock" -Confirm:$false
```

To pause blocking temporarily without removing it, just end the running
"pythonw.exe" process in Task Manager, or edit `config.json` to set a
time window that doesn't apply (e.g. `start_time` and `end_time` both
`"00:00"`).

## Known limitations

- Closes blocked apps abruptly (like ending a task) — any unsaved work in
  that app will be lost. Save before the blocking window starts.
- Does not block browser-based access to websites — only native .exe
  programs. If your target is a website rather than an app, you'd need a
  different approach (e.g. hosts file edits or browser extensions).
- Does not survive Safe Mode, and can be disabled by anyone with admin
  rights on the machine — by design, since this is meant to be cooperative.
