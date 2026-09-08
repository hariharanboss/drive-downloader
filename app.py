"""DriveFetch — Download directly to Google Drive.

Run locally:
    pip install -r requirements.txt
    python app.py

Run in Colab: open DriveDownloader.ipynb and run all cells.
"""

from __future__ import annotations

import traceback
from pathlib import Path

import gradio as gr

from src.downloaders import (
    YOUTUBE_QUALITY_MAP,
    detect_link_type,
    download_direct,
    download_gdrive_shared,
    download_youtube,
    drive_storage,
    get_download_root,
    human_size,
    list_downloads,
)

APP_TITLE = "DriveFetch"
APP_SUB = "Direct • YouTube • Drive Shared — straight to Google Drive"

CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

.gradio-container { max-width: 1080px !important; margin: 0 auto !important;
  font-family: 'Inter', system-ui, sans-serif !important;
  background: radial-gradient(1200px 500px at 50% -10%, #1e2a5a 0%, #0a0e1a 55%) !important;
  color: #e8ecf4 !important; }

.hero { background: linear-gradient(135deg, rgba(99,102,241,.18), rgba(34,211,238,.12));
  border: 1px solid rgba(148,163,184,.18); border-radius: 20px;
  padding: 28px 28px 22px 28px; margin-bottom: 18px;
  box-shadow: 0 20px 60px rgba(0,0,0,.45); backdrop-filter: blur(12px); }
.hero h1 { font-size: 34px !important; font-weight: 800 !important; margin: 0 !important;
  letter-spacing: -0.5px; background: linear-gradient(90deg,#fff,#a5b4fc 55%,#67e8f9);
  -webkit-background-clip: text; background-clip: text; color: transparent !important; }
.hero p { color: #9aa7c2 !important; margin: 8px 0 0 0 !important; font-size: 15px !important; }
.badges { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 14px; }
.badge { font-size: 12px; font-weight: 600; padding: 6px 12px; border-radius: 999px;
  background: rgba(148,163,184,.12); border: 1px solid rgba(148,163,184,.22); color: #cbd5e1; }
.badge.dot::before { content: '● '; font-size: 9px; }
.b-green::before { color: #34d399; } .b-blue::before { color: #60a5fa; } .b-purple::before { color: #a78bfa; }

.storage-bar { background: rgba(148,163,184,.12); border: 1px solid rgba(148,163,184,.18);
  border-radius: 14px; padding: 14px 16px; margin: 14px 0; font-size: 13px; color: #9aa7c2; }
.storage-bar b { color: #e2e8f0; }
.meter { height: 8px; border-radius: 999px; background: rgba(148,163,184,.15); overflow: hidden; margin-top: 8px; }
.meter > div { height: 100%; border-radius: 999px;
  background: linear-gradient(90deg,#6366f1,#22d3ee); transition: width .5s; }

.gr-button-primary { background: linear-gradient(135deg,#6366f1,#8b5cf6 55%,#06b6d4) !important;
  border: none !important; font-weight: 700 !important; border-radius: 12px !important;
  padding: 12px 20px !important; box-shadow: 0 8px 24px rgba(99,102,241,.4) !important; }
.gr-button-primary:hover { filter: brightness(1.1); transform: translateY(-1px); }
button { border-radius: 12px !important; }

input, textarea, select { border-radius: 12px !important;
  background: rgba(15,23,42,.8) !important; border: 1px solid rgba(148,163,184,.25) !important;
  color: #e2e8f0 !important; }
input:focus, textarea:focus { border-color: #6366f1 !important;
  box-shadow: 0 0 0 3px rgba(99,102,241,.25) !important; }

.tabs { background: rgba(15,23,42,.6); border: 1px solid rgba(148,163,184,.15);
  border-radius: 18px; padding: 18px; backdrop-filter: blur(10px); }
.result-ok { background: rgba(52,211,153,.1); border: 1px solid rgba(52,211,153,.3);
  border-radius: 12px; padding: 12px 14px; color: #a7f3d0; font-size: 14px; }
.result-err { background: rgba(248,113,113,.1); border: 1px solid rgba(248,113,113,.3);
  border-radius: 12px; padding: 12px 14px; color: #fecaca; font-size: 14px; }
.mono { font-family: 'JetBrains Mono', monospace !important; font-size: 12.5px !important; }
.footer { text-align: center; color: #64748b; font-size: 12.5px; margin-top: 18px; padding-bottom: 10px; }
.footer a { color: #818cf8; text-decoration: none; }
label { color: #cbd5e1 !important; font-weight: 600 !important; }
"""


def _storage_html() -> str:
    s = drive_storage()
    total = s["total"] or 1
    pct = min(100, round(s["used"] / total * 100, 1))
    return f"""
    <div class="storage-bar">
      <b>📁 {s['root']}</b> &nbsp;•&nbsp; Used <b>{s['used_h']}</b> / {s['total_h']}
      &nbsp;•&nbsp; Free <b>{s['free_h']}</b> &nbsp;•&nbsp; {pct}%
      <div class="meter"><div style="width:{pct}%"></div></div>
    </div>
    """


def _ok(msg: str) -> str:
    return f'<div class="result-ok">✅ {msg}</div>'


def _err(msg: str) -> str:
    return f'<div class="result-err">❌ {msg}</div>'


def _gr_progress_adapter(gr_progress):
    def _cb(done: int, total: int, name: str):
        try:
            if total:
                gr_progress((done / total), desc=f"{name} — {human_size(done)}/{human_size(total)}")
            else:
                gr_progress(None, desc=f"{name} — {human_size(done)}")
        except Exception:
            pass
    return _cb


def handle_direct(url, filename, subfolder, progress=gr.Progress(track_tqdm=True)):
    if not url or not url.strip():
        return _err("Paste a direct download link first."), _storage_html()
    try:
        dest = download_direct(url, custom_filename=filename or "",
                               subfolder=subfolder or "",
                               progress=_gr_progress_adapter(progress))
        size = dest.stat().st_size if dest.is_file() else 0
        return _ok(f"Saved <span class='mono'>{dest.name}</span> ({human_size(size)})<br><span class='mono'>{dest}</span>"), _storage_html()
    except Exception as e:
        traceback.print_exc()
        return _err(f"Direct download failed: {e}"), _storage_html()


def handle_youtube(url, quality, subfolder, progress=gr.Progress(track_tqdm=True)):
    if not url or not url.strip():
        return _err("Paste a YouTube / video link first."), _storage_html()
    try:
        dest = download_youtube(url, quality=quality, subfolder=subfolder or "",
                                progress=_gr_progress_adapter(progress))
        size = dest.stat().st_size if dest.is_file() else 0
        return _ok(f"Saved <span class='mono'>{dest.name}</span> ({human_size(size)})<br><span class='mono'>{dest}</span>"), _storage_html()
    except Exception as e:
        traceback.print_exc()
        return _err(f"Video download failed: {e}"), _storage_html()


def handle_gdrive(url, subfolder, progress=gr.Progress(track_tqdm=True)):
    if not url or not url.strip():
        return _err("Paste a Google Drive shared link first (Anyone with the link)."), _storage_html()
    try:
        dest = download_gdrive_shared(url, subfolder=subfolder or "",
                                      progress=_gr_progress_adapter(progress))
        if dest.is_file():
            size = dest.stat().st_size
            return _ok(f"Saved <span class='mono'>{dest.name}</span> ({human_size(size)})<br><span class='mono'>{dest}</span>"), _storage_html()
        return _ok(f"Folder saved: <span class='mono'>{dest}</span>"), _storage_html()
    except Exception as e:
        traceback.print_exc()
        return _err(f"Shared-link download failed: {e}. Make sure link is public."), _storage_html()


def handle_bulk(text, subfolder, progress=gr.Progress(track_tqdm=True)):
    lines = [l.strip() for l in (text or "").splitlines() if l.strip()]
    if not lines:
        return _err("Paste one URL per line first."), _storage_html()
    results = []
    cb = _gr_progress_adapter(progress)
    for i, url in enumerate(lines, 1):
        try:
            progress((i - 1) / len(lines), desc=f"[{i}/{len(lines)}] {url[:60]}")
            kind = detect_link_type(url)
            if kind == "gdrive":
                d = download_gdrive_shared(url, subfolder=subfolder or "", progress=cb)
            elif kind == "youtube":
                d = download_youtube(url, subfolder=subfolder or "", progress=cb)
            else:
                d = download_direct(url, subfolder=subfolder or "", progress=cb)
            results.append(f"✅ [{kind}] {Path(d).name}")
        except Exception as e:
            results.append(f"❌ {url[:70]} — {e}")
    html = "<br>".join(results)
    ok_count = sum(1 for r in results if r.startswith("✅"))
    return f'<div class="result-ok">{ok_count}/{len(lines)} done<br>{html}</div>', _storage_html()


def refresh_files():
    rows = list_downloads()
    if not rows:
        return [], _storage_html()
    data = [[r["name"], r["size_h"]] for r in rows]
    return data, _storage_html()


def build_demo() -> gr.Blocks:
    with gr.Blocks(title="DriveFetch — Save to Drive", css=CUSTOM_CSS,
                   theme=gr.themes.Soft(primary_hue="indigo")) as demo:
        gr.HTML(f"""
        <div class="hero">
          <h1>⬇️ {APP_TITLE}</h1>
          <p>{APP_SUB}. Files land directly in Drive — no Colab disk fill-ups, resumable, with live progress.</p>
          <div class="badges">
            <span class="badge dot b-green">Direct HTTP</span>
            <span class="badge dot b-blue">YouTube + 1000 sites</span>
            <span class="badge dot b-purple">Drive shared links</span>
            <span class="badge">⚡ Bulk mode</span>
            <span class="badge">🔒 Private — runs in your Colab</span>
          </div>
        </div>
        """)

        storage = gr.HTML(_storage_html())

        with gr.Group(elem_classes=["tabs"]):
            with gr.Tabs():
                with gr.Tab("🔗 Direct Link"):
                    gr.Markdown("Paste any direct file URL (`https://…/file.zip`). Supports resume with `-c` logic.")
                    d_url = gr.Textbox(label="File URL", placeholder="https://example.com/bigfile.zip")
                    with gr.Row():
                        d_name = gr.Textbox(label="Custom filename (optional)", placeholder="myfile.zip")
                        d_folder = gr.Textbox(label="Subfolder in Downloads (optional)", placeholder="movies / software")
                    d_btn = gr.Button("⬇ Download to Drive", variant="primary")
                    d_out = gr.HTML()
                    d_btn.click(handle_direct, [d_url, d_name, d_folder], [d_out, storage])

                with gr.Tab("▶ YouTube / Video"):
                    gr.Markdown("YouTube, TikTok, Instagram, X, Facebook, Twitch, Vimeo + 1000 sites via yt-dlp.")
                    y_url = gr.Textbox(label="Video / playlist URL", placeholder="https://youtube.com/watch?v=…")
                    with gr.Row():
                        y_q = gr.Dropdown(list(YOUTUBE_QUALITY_MAP.keys()),
                                          value="Best (up to 1080p)", label="Quality")
                        y_folder = gr.Textbox(label="Subfolder (optional)", placeholder="videos")
                    y_btn = gr.Button("⬇ Download Video", variant="primary")
                    y_out = gr.HTML()
                    y_btn.click(handle_youtube, [y_url, y_q, y_folder], [y_out, storage])

                with gr.Tab("📁 Drive Shared Link"):
                    gr.Markdown("Paste a **Anyone with the link** Google Drive file/folder link. Folders are cloned recursively.")
                    g_url = gr.Textbox(label="Shared link", placeholder="https://drive.google.com/file/d/…/view?usp=sharing")
                    g_folder = gr.Textbox(label="Subfolder (optional)", placeholder="shared")
                    g_btn = gr.Button("⬇ Save to My Drive", variant="primary")
                    g_out = gr.HTML()
                    g_btn.click(handle_gdrive, [g_url, g_folder], [g_out, storage])

                with gr.Tab("⚡ Bulk"):
                    gr.Markdown("One URL per line. Auto-detects Direct / Video / Drive links.")
                    b_text = gr.Textbox(label="URLs (one per line)", lines=6,
                                        placeholder="https://example.com/a.zip\nhttps://youtube.com/watch?v=…\nhttps://drive.google.com/file/d/…")
                    b_folder = gr.Textbox(label="Subfolder (optional)", placeholder="batch-01")
                    b_btn = gr.Button("⬇ Download All", variant="primary")
                    b_out = gr.HTML()
                    b_btn.click(handle_bulk, [b_text, b_folder], [b_out, storage])

                with gr.Tab("📂 Files"):
                    gr.Markdown(f"Contents of `{get_download_root()}` (newest first).")
                    f_btn = gr.Button("🔄 Refresh")
                    f_table = gr.Dataframe(headers=["File", "Size"], datatype=["str", "str"],
                                           interactive=False, wrap=True)
                    f_btn.click(refresh_files, None, [f_table, storage])
                    demo.load(refresh_files, None, [f_table, storage])

        gr.HTML('<div class="footer">DriveFetch • Colab + Local • yt-dlp • gdown • Gradio &nbsp;—&nbsp; only download content you have rights to.</div>')

    return demo


demo = build_demo()

if __name__ == "__main__":
    import os
    in_colab = os.path.exists("/content") or os.path.exists("/content/drive")
    demo.launch(share=in_colab, server_name="0.0.0.0", server_port=7860)
