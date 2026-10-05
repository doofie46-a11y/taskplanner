# 📋 TaskPlanner

A simple, private daily task planner for your desktop. Everything stays on your computer:
no account, no cloud, no tracking.

*🇮🇹 Pianificatore di attività giornaliere per desktop: i dati restano sul tuo computer,
nessun account, nessun cloud. Interfaccia in italiano e inglese.*

## Features

- **Daily view** with priorities, times, pinned tasks and custom card colors
- **Recurring tasks** (daily, weekly, monthly, first Monday, last Friday, …) with end date or max occurrences
- **Automatic rollover**: unfinished tasks move to today, with optional priority escalation the longer they wait
- **Categories and groups** with live filters and counters
- **Attachments** via drag & drop
- **Trash** with automatic cleanup after 7 days
- **Statistics** and **export** to CSV, JSON, TXT and Markdown
- **Contaschei**: a small personal income/expense tracker with recurring entries and period reports
- **Dark mode**, Italian and English UI
- **Outlook integration** on Windows (create events and tasks)

## Download

Get the latest version for Windows or Linux from the
[Releases page](https://github.com/doofie46-a11y/taskplanner/releases/latest).
It is a single executable: no installation needed.

**macOS:** no prebuilt binary for now (I have no Mac to test it on). TaskPlanner runs fine
[from source](#run-from-source); help testing a macOS build is welcome.

| OS | First launch |
|---|---|
| Windows | See [Windows SmartScreen](#windows-smartscreen) below. Requires the WebView2 runtime (preinstalled on Windows 10 21H2+ and Windows 11) |
| Linux | `chmod +x TaskPlanner-*-linux && ./TaskPlanner-*-linux` |

### Windows SmartScreen

The Windows executable is not code-signed yet, so on first launch Windows may show
*"Windows protected your PC"* with *Unknown publisher*. This warning appears for any new
unsigned program, not because something was detected in it. Click **More info** →
**Run anyway**; Windows will not ask again for that file.

If you prefer to check the file first, [verify its checksum](#verify-the-download) or
[run TaskPlanner from source](#run-from-source).

### Verify the download

Every release includes a `SHA256SUMS.txt` file with the SHA-256 checksum of each executable,
computed by the same GitHub Actions run that built them. Compare it with your download:

```powershell
# Windows (PowerShell)
Get-FileHash .\TaskPlanner-*-windows.exe -Algorithm SHA256
```

```bash
# Linux (in the download folder, with SHA256SUMS.txt next to the executable)
sha256sum --check --ignore-missing SHA256SUMS.txt
```

### Where your data lives

| OS | Folder |
|---|---|
| Windows | `%LOCALAPPDATA%\TaskPlanner\TaskPlanner\` |
| macOS | `~/Library/Application Support/TaskPlanner/` |
| Linux | `~/.local/share/TaskPlanner/` |

The database (`taskplanner.db`, SQLite) and attachments are in that folder: back it up to keep your data safe.
Set `TASKPLANNER_DATA=/some/path` to use a different folder.

### Uninstall

TaskPlanner does not install anything: delete the executable, and delete the data folder
above if you also want to remove your tasks.

## Privacy

TaskPlanner has no telemetry, no analytics and no update checks. The desktop app does not
connect to the internet on its own: your data stays in the local folder above. A web page
opens only when you click a link (the Ko-fi page, or Google Calendar when you add a task
to it). The Outlook integration talks only to the Outlook installed on your PC.

In [server mode](#server-mode) the data lives on the server of whoever runs it, and sign-in
goes through Google.

## Code signing policy

The Windows executable is not signed yet: free code signing from
[SignPath Foundation](https://signpath.org) has been requested. Signed releases will be
built only by the GitHub Actions workflow in this repository, from its own source code.

- Committers and reviewers: [doofie46-a11y](https://github.com/doofie46-a11y)
- Approver (authorizes each signed release): [doofie46-a11y](https://github.com/doofie46-a11y)

## Run from source

Requires Python 3.11+.

```bash
git clone https://github.com/doofie46-a11y/taskplanner.git
cd taskplanner
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements/desktop.txt
python app_desktop.py
```

### Build the executable

```bash
pip install -r requirements/desktop.txt pillow
python desktop/make_icons.py
pyinstaller taskplanner_desktop.spec    # output in dist/
```

Releases are built automatically by GitHub Actions for all three platforms when a `vX.Y.Z` tag is pushed.

## Server mode

The same codebase can also run as a multi-user web app (PostgreSQL + Google sign-in) with
`gunicorn app_server:app`. See `.env.example` for the required settings.

## Contributing

Bug reports and pull requests are welcome. User-facing strings must be wrapped in `_("…")`
and translated in `translations/en/LC_MESSAGES/messages.po` (Italian is the source language).

## Support

If TaskPlanner is useful to you, you can [buy me a beer 🍺](https://ko-fi.com/claudioruffina).

## License

[GNU GPL v3.0](LICENSE). You may use, modify and redistribute TaskPlanner; modified versions
you distribute must be released under the same license, with source code.
