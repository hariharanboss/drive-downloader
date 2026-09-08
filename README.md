# ⬇️ DriveFetch — Download Directly to Google Drive

Professional downloader UI that saves **straight to Google Drive** when run in Colab, or to `./downloads` locally.

Supports:
- 🔗 **Direct HTTP(S) links** — streamed, resumable, live progress
- ▶ **YouTube + 1000 sites** — via `yt-dlp` (quality picker, MP3 mode, playlists)
- 📁 **Google Drive shared links** — file + folder clone via `gdown`
- ⚡ **Bulk mode** — paste 100 URLs, auto-detects type
- 📂 **Files tab** — browse what landed in Drive + storage meter

Stack: Python + Gradio (custom pro dark UI) + yt-dlp + gdown + requests.

## 🚀 Run in Colab (recommended — saves to Drive)

1. Open https://colab.research.google.com → Upload `DriveDownloader.ipynb` from this repo
2. Runtime → Run all
3. Mount Drive when asked
4. Click the `*.gradio.live` link → pro UI opens
5. Paste link → Download → check Drive > Downloads

Or one cell manually:
```python
from google.colab import drive
drive.mount('/content/drive')
!git clone https://github.com/YOUR-USER/drive-downloader.git
%cd drive-downloader
!pip -q install -r requirements.txt
!python app.py  # uses share=True in Colab
```

## 💻 Run locally

```bash
git clone https://github.com/YOUR-USER/drive-downloader.git
cd drive-downloader
pip install -r requirements.txt
python app.py
# open http://127.0.0.1:7860
```

## 📁 Structure

```
drive-downloader/
  app.py                 # Gradio pro UI (header, tabs, storage meter, history)
  src/
    downloaders.py       # direct / youtube / gdrive engines + Drive detection
  DriveDownloader.ipynb  # 1-click Colab launcher
  requirements.txt
```

## ⚠️ Notes

- Drive shared links must be **Anyone with the link**.
- Only download content you own or have rights to. YouTube downloads must respect YouTube ToS / copyright.
- Colab path: `/content/drive/MyDrive/Downloads`. Local path: `./downloads`.
- For 4K / cookies / private videos, extend `yt-dlp` opts in `src/downloaders.py`.

## 📸 UI

Dark glassmorphism hero, badge row, storage meter, tabbed cards (Direct / YouTube / Drive / Bulk / Files), gradient CTA, toasts, responsive.
