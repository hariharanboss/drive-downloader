<div align="center">

# ⬇️ DriveFetch

**A professional downloader web UI that saves files directly to Google Drive.**

Run it in Google Colab — downloads land straight in `MyDrive/Downloads`, never filling the Colab disk.

[![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/#getting-started) [![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org) [![License](https://img.shields.io/badge/license-MIT-green)](LICENSE) [![Gradio](https://img.shields.io/badge/UI-Gradio-orange)](https://gradio.app)

</div>

---

## ✨ Features

| Feature | What it does |
|---|---|
| 🔗 **Direct links** | Any `http(s)` file URL — streamed, **resumable**, with live progress, speed & ETA |
| ▶ **YouTube + 1000 sites** | Via `yt-dlp` — quality picker (1080p/720p/480p), MP3 extraction, playlists |
| 📁 **Drive shared links** | Public files **and folders** via `gdown` — folders cloned recursively |
| ⚡ **Bulk mode** | Paste many URLs (one per line) — type auto-detected per link |
| 📊 **Live status bar** | Permanent bottom panel: filename, %, size, speed, ETA — with success/error states |
| 🌗 **Dark / Light theme** | One-click toggle, remembers your choice, distinct typography per theme |
| 📂 **Files browser** | See exactly what landed in Drive, with sizes — auto-refreshes after each download |
| 💾 **Storage meter** | Live free-space readout so you know before you run out |

**Stack:** Python · Gradio 6 · yt-dlp · gdown · requests

---

## 🚀 Quick Start — Google Colab (recommended)

Files save to **Drive → Downloads**. No Colab disk involved.

1. Download [`DriveDownloader.ipynb`](DriveDownloader.ipynb) from this repo
2. Open [Google Colab](https://colab.research.google.com), **File → Upload notebook**
3. **Runtime → Run all** → authorize the Drive mount when prompted
4. Cell 3 prints a `*.gradio.live` link — **click it** to open the UI
5. Paste any link, hit download, check Drive

> The notebook is **self-healing**: broken/partial checkouts are wiped and re-cloned automatically, and each cell validates its state before running.

<details>
<summary><b>Prefer a single cell? Click to expand</b></summary>

```python
from google.colab import drive
drive.mount('/content/drive')

!git clone https://github.com/hariharanboss/drive-downloader.git
%cd drive-downloader
!pip -q install -r requirements.txt
!python app.py   # prints a public gradio.live link
```
</details>

## 💻 Run locally

```bash
git clone https://github.com/hariharanboss/drive-downloader.git
cd drive-downloader
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:7860` — files save to `./downloads/`.

---

## 🖥️ The UI

```
┌────────────────────────────────────────────────────┐
│  ⬇ DriveFetch v1.4        [Dark ◐ / Light]        │
│  badges: Direct • YouTube • Drive • Bulk • Private │
├────────────────────────────────────────────────────┤
│  🔗 Direct │ ▶ YouTube │ 📁 Drive │ ⚡ Bulk │ 📂 Files │
│                                                    │
│  [ URL input ] [ filename ] [ subfolder ]         │
│  [      ⬇ Download to Drive      ]                │
│  ✓ result appears here                            │
├────────────────────────────────────────────────────┤
│  ═══ Download Status ═══  ← permanent bottom bar   │
│  ⟳ filename • 43% • 210 MB/487 MB • 8.2 MB/s • ETA 34s │
└────────────────────────────────────────────────────┘
```

- **Tabs** separate the four download modes; every mode supports an optional subfolder (`Downloads/movies/...`)
- **Status bar** has four states — idle, running, done (green), error (red) — and never disappears
- Fully responsive; mobile gets full-width buttons and a compact bar

---

## 🔧 Use as a Python library

The download engines are importable — no UI required:

```python
from src.downloaders import download_direct, download_youtube, download_gdrive_shared

download_direct("https://example.com/big-file.zip")              # → Path to saved file
download_youtube("https://youtube.com/watch?v=...", quality="720p")
download_gdrive_shared("https://drive.google.com/file/d/.../view")
```

All functions return a `Path` to the saved file. Destination root is auto-detected:
- **Colab:** `/content/drive/MyDrive/Downloads`
- **Local:** `./downloads/`

Custom progress is easy — pass a callback `f(done_bytes, total_bytes, filename)`.

---

## 📁 Project structure

```
drive-downloader/
├── app.py                  # Gradio UI — layout, theming, live status bar, event wiring
├── src/
│   ├── __init__.py
│   └── downloaders.py       # Download engines: direct / yt-dlp / gdown + link detection
├── DriveDownloader.ipynb    # One-click self-healing Colab launcher
├── requirements.txt         # gradio, yt-dlp, gdown, requests
└── README.md
```

---

## ❓ FAQ

<details>
<summary><b>Where do files go?</b></summary>

Colab: **Drive → Downloads** (`/content/drive/MyDrive/Downloads`). Locally: `./downloads/`. Use the *Subfolder* field in any tab to organize (e.g. `movies`, `software`).
</details>

<details>
<summary><b>Why does my Drive folder link fail?</b></summary>

Shared links must be set to **"Anyone with the link"**. Restricted/private links can't be fetched by `gdown`.
</details>

<details>
<summary><b>What does the storage bar actually show?</b></summary>

Free space on the **machine running the app** — in Colab that's the VM disk (where Drive is mounted), not your Drive quota. It's the number that matters for "can this download finish?"
</details>

<details>
<summary><b>A download got interrupted — do I restart from zero?</b></summary>

Direct links resume automatically: re-run and it continues from the already-downloaded bytes (HTTP Range).
</details>

<details>
<summary><b>Is my data private?</b></summary>

The UI runs inside *your* Colab session — links go to the sites you're downloading from, nothing else. Note: the temporary `gradio.live` link is accessible to anyone who has it; stop cell 3 when done.
</details>

---

## ⚠️ Disclaimer

Download only content you own or have the legal right to obtain. YouTube downloads are subject to YouTube's Terms of Service; respect copyright in your jurisdiction. The authors take no responsibility for misuse.

---

## 🗺️ Roadmap

- [ ] Per-download cancel button
- [ ] Download queue with concurrency control
- [ ] 4K / cookie-based (private) video support
- [ ] Telegram bot front-end
- [ ] Docker image for self-hosting

## 🤝 Contributing

Issues and PRs welcome — keep the UI code in `app.py`, engine logic in `src/downloaders.py`, and follow the existing style.

---

<div align="center">

**Made with Python, Gradio, and too much GitHub Copilot**

</div>
