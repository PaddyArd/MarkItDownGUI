# MarkItDown GUI

A desktop app with a Microsoft Fluent Design look for converting documents to Markdown, powered by
[microsoft/markitdown](https://github.com/microsoft/markitdown). Built with Python and
[PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets).

> Unofficial project. It is not affiliated with or endorsed by Microsoft.

## Features

- **Convert** a single file or URL (including YouTube links). Drag and drop or browse.
- **Live preview**: rendered Markdown and raw Markdown tabs; copy to clipboard or save as `.md`.
- **Batch mode**: add files or whole folders, convert all, see per-file status, cancel at any time.
  Existing `.md` files are never overwritten (`name (1).md` is used instead).
- **Settings**: light/dark/system theme, batch output folder, plugins, Azure Document Intelligence,
  OpenAI model for image descriptions.
- **Crash-isolated**: conversion runs in a separate process, so a failing converter cannot take down the window.

Supported inputs are whatever your installed markitdown supports: PDF, Word, PowerPoint, Excel, HTML,
CSV, JSON, XML, images, audio, ZIP, EPUB and more.

## Requirements

- Windows 10/11 (developed for Windows; should also run on macOS/Linux)
- Python 3.10 - 3.13 recommended. Very new Python releases may lack wheels for some dependencies.

## Quick start

```bat
run.bat
```

This creates `.venv`, installs `requirements.txt` and starts the app. Manually:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Build a Windows executable

```bat
build.bat
```

Output: `dist\MarkItDown\MarkItDown.exe` (PyInstaller, one-folder build).

## Optional services

Configure these on the **Settings** page.

| Setting | Purpose |
| --- | --- |
| Azure Document Intelligence endpoint | Higher-fidelity PDF/Office/image conversion (needs Azure credentials in your environment) |
| OpenAI API key + model | Describe images found in documents |
| Enable plugins | Load third-party markitdown plugins |

Settings are stored in the Windows registry under `HKCU\Software\MarkItDownGUI`. The API key is stored
**unencrypted**; do not use a key you cannot afford to expose.

## Troubleshooting

See [docs/troubleshooting.md](docs/troubleshooting.md). Errors are appended to
`%USERPROFILE%\MarkItDownGUI-crash.log`.

## Documentation

- [Architecture](docs/architecture.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Contributing](CONTRIBUTING.md)
- [Changelog](CHANGELOG.md)

## License

MIT, see [LICENSE](LICENSE). markitdown is also MIT-licensed; other dependencies carry their own licenses
(notably PyQt5 is GPL v3 / commercial, and PyQt-Fluent-Widgets is GPLv3 for non-commercial use with a
commercial license available). Check these before distributing binaries or using the app commercially.
