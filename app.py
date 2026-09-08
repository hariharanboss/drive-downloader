"""DriveFetch — Download directly to Google Drive.

Run locally:
    pip install -r requirements.txt
    python app.py

Run in Colab: open DriveDownloader.ipynb and run all cells.
"""

from __future__ import annotations

import html
import threading
import time
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
    is_gdrive_folder,
    list_downloads,
)

APP_TITLE = "DriveFetch"
APP_SUB = "Direct • YouTube • Drive Shared — straight to Google Drive"

# NOTE: Light = Plus Jakarta Sans, Dark = Inter (deliberately different per request).
# Theme is toggled via a switch that adds/removes `.dark` on <html>/<body>.
CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

/* ---------- theme tokens ---------- */
.gradio-container {
  --df-bg: #f4f6fb;
  --df-card: #ffffff;
  --df-text: #0f172a;
  --df-muted: #5b6b82;
  --df-border: rgba(15,23,42,.10);
  --df-input: #ffffff;
  --df-hero: linear-gradient(135deg, #e0e7ff 0%, #f0fdfa 100%);
  --df-badge-bg: rgba(15,23,42,.05);
  --df-shadow: 0 12px 32px rgba(15,23,42,.08);
}
.dark .gradio-container, html.dark .gradio-container, body.dark .gradio-container {
  --df-bg: #0a0e1a;
  --df-card: rgba(15,23,42,.62);
  --df-text: #e8ecf4;
  --df-muted: #9aa7c2;
  --df-border: rgba(148,163,184,.18);
  --df-input: rgba(15,23,42,.85);
  --df-hero: linear-gradient(135deg, rgba(99,102,241,.20), rgba(34,211,238,.12));
  --df-badge-bg: rgba(148,163,184,.12);
  --df-shadow: 0 20px 60px rgba(0,0,0,.45);
}

/* ---------- base: fonts DIFFER per theme ---------- */
.gradio-container {
  max-width: 1080px !important; margin: 0 auto !important;
  font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif !important;
  background: radial-gradient(1100px 420px at 50% -10%, #dbeafe 0%, var(--df-bg) 60%) !important;
  color: var(--df-text) !important;
  transition: background .25s ease, color .25s ease;
}
.dark .gradio-container, html.dark .gradio-container, body.dark .gradio-container {
  font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
  background: radial-gradient(1200px 500px at 50% -10%, #1e2a5a 0%, #0a0e1a 55%) !important;
}

/* ---------- hero ---------- */
.hero { background: var(--df-hero); border: 1px solid var(--df-border);
  border-radius: 20px; padding: 22px; margin-bottom: 16px;
  box-shadow: var(--df-shadow); backdrop-filter: blur(12px);
  display: flex; gap: 16px; justify-content: space-between; align-items: flex-start; }
.hero-main { display: flex; gap: 14px; align-items: flex-start; flex: 1; min-width: 0; }
.logo { width: 46px; height: 46px; border-radius: 14px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 19px; color: #fff;
  background: linear-gradient(135deg,#6366f1,#8b5cf6 55%,#06b6d4);
  box-shadow: 0 8px 20px rgba(99,102,241,.4); }
.hero h1 { font-size: 30px !important; margin: 0 !important; line-height: 1.1 !important;
  /* light theme heading style */
  font-family: 'Plus Jakarta Sans', sans-serif !important; font-weight: 800 !important;
  letter-spacing: -0.8px !important; color: #0f172a !important; }
.dark .hero h1, html.dark .hero h1 { font-family: 'Inter', sans-serif !important;
  font-weight: 800 !important; letter-spacing: -0.5px !important;
  background: linear-gradient(90deg,#fff,#a5b4fc 55%,#67e8f9);
  -webkit-background-clip: text; background-clip: text; color: transparent !important; }
.hero p { color: var(--df-muted) !important; margin: 6px 0 0 0 !important; font-size: 14px !important; }
.version-pill { display: inline-block; font-size: 11px; font-weight: 700; margin-left: 8px;
  padding: 3px 9px; border-radius: 999px; vertical-align: middle;
  background: rgba(99,102,241,.14); color: #6366f1; border: 1px solid rgba(99,102,241,.3); }
.badges { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
.badge { font-size: 12px; font-weight: 600; padding: 6px 12px; border-radius: 999px;
  background: var(--df-badge-bg); border: 1px solid var(--df-border); color: var(--df-muted); }
.badge.dot::before { content: '● '; font-size: 9px; }
.b-green::before { color: #10b981; } .b-blue::before { color: #3b82f6; } .b-purple::before { color: #8b5cf6; }

/* ---------- theme toggle switch ---------- */
.theme-box { display: flex; flex-direction: column; align-items: center; gap: 6px;
  flex-shrink: 0; padding-top: 4px; }
.theme-box small { font-size: 11px; font-weight: 700; color: var(--df-muted); letter-spacing: .4px; }
.switch { position: relative; display: inline-block; width: 52px; height: 28px; }
.switch input { opacity: 0; width: 0; height: 0; }
.slider { position: absolute; cursor: pointer; inset: 0; border-radius: 999px;
  background: #cbd5e1; border: 1px solid var(--df-border); transition: .25s; }
.slider:before { content: '☀'; position: absolute; height: 22px; width: 22px; left: 3px; top: 2px;
  background: #fff; border-radius: 50%; transition: .25s;
  display: flex; align-items: center; justify-content: center; font-size: 13px;
  box-shadow: 0 2px 6px rgba(0,0,0,.25); }
.switch input:checked + .slider { background: linear-gradient(90deg,#6366f1,#06b6d4); }
.switch input:checked + .slider:before { transform: translateX(23px); content: '☾'; }

/* ---------- cards / inputs / buttons ---------- */
.storage-bar { background: var(--df-card); border: 1px solid var(--df-border);
  border-radius: 14px; padding: 14px 16px; margin: 14px 0; font-size: 13px; color: var(--df-muted); }
.storage-bar b { color: var(--df-text); }
.meter { height: 8px; border-radius: 999px; background: rgba(148,163,184,.22); overflow: hidden; margin-top: 8px; }
.meter > div { height: 100%; border-radius: 999px;
  background: linear-gradient(90deg,#6366f1,#22d3ee); transition: width .5s; }

.gr-button-primary { background: linear-gradient(135deg,#6366f1,#8b5cf6 55%,#06b6d4) !important;
  border: none !important; font-weight: 700 !important; border-radius: 12px !important;
  padding: 12px 20px !important; box-shadow: 0 8px 24px rgba(99,102,241,.35) !important; }
.gr-button-primary:hover { filter: brightness(1.07); transform: translateY(-1px); }
button { border-radius: 12px !important; }

input, textarea, select { border-radius: 12px !important;
  background: var(--df-input) !important; border: 1px solid var(--df-border) !important;
  color: var(--df-text) !important; }
input:focus, textarea:focus { border-color: #6366f1 !important;
  box-shadow: 0 0 0 3px rgba(99,102,241,.22) !important; }

.tabs { background: var(--df-card); border: 1px solid var(--df-border);
  border-radius: 18px; padding: 18px; backdrop-filter: blur(10px); box-shadow: var(--df-shadow); }
.result-ok { background: rgba(52,211,153,.12); border: 1px solid rgba(52,211,153,.35);
  border-radius: 12px; padding: 12px 14px; color: #065f46; font-size: 14px; }
.dark .result-ok, html.dark .result-ok { color: #a7f3d0; }
.result-err { background: rgba(248,113,113,.10); border: 1px solid rgba(248,113,113,.35);
  border-radius: 12px; padding: 12px 14px; color: #991b1b; font-size: 14px; }
.dark .result-err, html.dark .result-err { color: #fecaca; }
.mono { font-family: 'JetBrains Mono', monospace !important; font-size: 12.5px !important; }
.footer { text-align: center; color: var(--df-muted); font-size: 12.5px; margin-top: 18px; padding-bottom: 10px; }
.footer a { color: #6366f1; text-decoration: none; }
label { color: var(--df-text) !important; font-weight: 600 !important; }

/* ---------- bottom-docked download status (both themes) ---------- */
.df-hidden { display: none !important; }
.df-dock { position: fixed; left: 50%; transform: translateX(-50%); bottom: 18px;
  z-index: 200; width: min(600px, calc(100vw - 32px));
  background: var(--df-card); border: 1px solid var(--df-border);
  border-radius: 16px; box-shadow: var(--df-shadow);
  padding: 14px 16px; color: var(--df-text); }
.df-row { display: flex; gap: 12px; align-items: center; }
.df-spin { width: 22px; height: 22px; flex-shrink: 0; border-radius: 50%;
  border: 3px solid rgba(148,163,184,.3); border-top-color: #6366f1;
  animation: dfspin .8s linear infinite; }
@keyframes dfspin { to { transform: rotate(360deg); } }
.df-meta { flex: 1; min-width: 0; }
.df-title { font-weight: 700; font-size: 13.5px; }
.df-file { font-family: 'JetBrains Mono', monospace; font-size: 12px;
  color: var(--df-muted); white-space: nowrap; overflow: hidden;
  text-overflow: ellipsis; }
.df-pct { font-weight: 800; font-size: 15px; font-variant-numeric: tabular-nums;
  flex-shrink: 0; }
.df-track { height: 10px; border-radius: 999px; background: rgba(148,163,184,.22);
  overflow: hidden; margin-top: 10px; }
.df-fill { height: 100%; border-radius: 999px;
  background: linear-gradient(90deg,#6366f1,#22d3ee); transition: width .3s ease; }
.df-track.df-ind .df-fill { width: 35% !important; animation: dfslide 1.2s ease-in-out infinite; }
@keyframes dfslide { 0% { margin-left: -35%; } 100% { margin-left: 100%; } }
.df-sub { margin-top: 8px; font-size: 12px; color: var(--df-muted);
  font-variant-numeric: tabular-nums; }
.result-pending { background: rgba(99,102,241,.08); border: 1px solid rgba(99,102,241,.3);
  border-radius: 12px; padding: 12px 14px; font-size: 14px; color: var(--df-text); }
div[role="tablist"] { overflow-x: auto !important; scrollbar-width: thin; }

/* ---------- mobile ---------- */
@media (max-width: 640px) {
  .hero { flex-direction: column; padding: 18px 16px; }
  .hero h1 { font-size: 24px !important; }
  .theme-box { flex-direction: row; align-self: flex-end; }
  .tabs { padding: 12px; border-radius: 14px; }
  .gr-button-primary, button.primary { width: 100% !important; }
  .df-dock { bottom: 10px; padding: 12px; }
}
"""


# Runs via launch(js=...) — Gradio strips <script> tags inside gr.HTML
# (they are injected via innerHTML and never execute), so the toggle logic
# must live here, not inline in the hero markup.
# CONTRACT (matches Gradio's own apps, e.g. themes/builder_app.py):
# `js` must be a zero-arg arrow FUNCTION string. The shell evals it and
# calls the result on load. An IIFE statement evals to `undefined`, so the
# shell's call throws on every page load — that was the load-time error.
THEME_JS = """() => {
  var KEY = 'drivefetch-theme';
  function apply(t){
    var dark = (t === 'dark');
    try {
      document.documentElement.classList.toggle('dark', dark);
      if (document.body) document.body.classList.toggle('dark', dark);
      var root = document.querySelector('.gradio-container');
      if (root) root.classList.toggle('dark', dark);
    } catch(e) {}
    var el = document.getElementById('df-theme-toggle');
    if (el) el.checked = dark;
    try { localStorage.setItem(KEY, t); } catch(e) {}
  }
  var init = 'dark';
  try {
    init = localStorage.getItem(KEY) ||
      (window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark');
  } catch(e) {}
  apply(init);
  // Gradio renders components asynchronously — delegate + re-sync.
  document.addEventListener('change', function(e){
    if (e.target && e.target.id === 'df-theme-toggle') {
      apply(e.target.checked ? 'dark' : 'light');
    }
  });
  var tries = 0;
  var timer = setInterval(function(){
    var el = document.getElementById('df-theme-toggle');
    if (el) {
      el.checked = document.documentElement.classList.contains('dark');
      clearInterval(timer);
    } else if (++tries > 40) { clearInterval(timer); }
  }, 250);
}"""


def _storage_html() -> str:
    s = drive_storage()
    total = s["total"] or 1
    pct = min(100, round(s["used"] / total * 100, 1))
    return f"""
    <div class="storage-bar" title="Free space on the machine running the app (Colab VM disk when in Colab)">
      <b>📁 {s['root']}</b> &nbsp;•&nbsp; Server disk used <b>{s['used_h']}</b> / {s['total_h']}
      &nbsp;•&nbsp; Free <b>{s['free_h']}</b> &nbsp;•&nbsp; {pct}%
      <div class="meter"><div style="width:{pct}%"></div></div>
    </div>
    """


def _ok(msg: str) -> str:
    return f'<div class="result-ok">✅ {msg}</div>'


def _err(msg: str) -> str:
    return f'<div class="result-err">❌ {msg}</div>'


class _LiveProgress:
    """Thread-safe progress state.

    Download backends write via ``cb`` from a worker thread; the handler
    generator polls ``snapshot()`` ~3x/sec and re-renders the bottom dock.
    Cheap attribute writes (no Gradio queue flooding, no flicker).
    """

    def __init__(self, label: str = ""):
        self._lock = threading.Lock()
        self.label = label
        self.name = ""
        self.done = 0
        self.total = 0
        self.start = time.time()

    def set_label(self, label: str):
        with self._lock:
            self.label = label

    def cb(self, done: int, total: int, name: str):
        with self._lock:
            self.done = max(int(done or 0), 0)
            self.total = int(total or 0)
            if name:
                self.name = name

    def snapshot(self):
        with self._lock:
            return (self.label, self.name, self.done, self.total, self.start)


def _dock_hidden() -> str:
    return '<div class="df-dock df-hidden" id="df-dock"></div>'


def _dock_html(label: str, name: str, done: int, total: int, start: float) -> str:
    """Bottom-docked status card. Determinate bar when total is known,
    shimmer indeterminate bar otherwise (same card, consistent look)."""
    elapsed = max(time.time() - start, 1e-6)
    speed = done / elapsed
    speed_h = f"{human_size(speed)}/s" if speed > 0 else "?/s"
    title = html.escape((label or "Downloading").strip()[:80])
    fname = html.escape((name or "starting…")[:80])
    if total:
        frac = min(max(done / total, 0.0), 1.0)
        eta = (total - done) / speed if speed > 0 else 0
        bar = (f'<div class="df-track"><div class="df-fill" '
               f'style="width:{frac * 100:.1f}%"></div></div>')
        pct = f"{frac * 100:.0f}%"
        sub = (f"{human_size(done)} / {human_size(total)} • {speed_h} • "
               f"ETA {eta:.0f}s")
    else:
        bar = '<div class="df-track df-ind"><div class="df-fill"></div></div>'
        pct = "•••"
        sub = f"{human_size(done)} downloaded • {speed_h}"
    return (
        f'<div class="df-dock" id="df-dock" role="status" aria-live="polite">'
        f'<div class="df-row"><span class="df-spin"></span>'
        f'<div class="df-meta"><div class="df-title">{title}</div>'
        f'<div class="df-file">{fname}</div></div>'
        f'<div class="df-pct">{pct}</div></div>'
        f'{bar}<div class="df-sub">{sub}</div></div>'
    )


def _pending(label: str) -> str:
    return (f'<div class="result-pending">⏳ {html.escape(label[:100])} — '
            f'watch the status bar at the bottom of the page…</div>')


def _file_rows():
    rows = list_downloads()
    return [[r["name"], r["size_h"]] for r in rows]


def _run_with_dock(label: str, worker):
    """Run blocking ``worker(state) -> result_html`` on a thread while
    streaming dock updates. Yields (result, storage, dock, files) tuples.

    The dock is visible for the whole download and hidden again on
    completion; the per-tab result area + Files tab update at the end.
    """
    st = _LiveProgress(label=label)
    box: dict = {}
    storage = _storage_html()
    files = _file_rows()

    def run():
        try:
            box["result"] = worker(st)
        except Exception:
            box["error"] = traceback.format_exc(limit=3)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    yield _pending(label), storage, _dock_html(*st.snapshot()), files
    while True:
        t.join(timeout=0.3)
        if not t.is_alive():
            break
        yield _pending(label), storage, _dock_html(*st.snapshot()), files
    if "error" in box:
        print(box["error"])
        last_line = html.escape(box["error"].strip().splitlines()[-1][:300])
        yield _err(f"Download failed: {last_line}"), _storage_html(), \
            _dock_hidden(), _file_rows()
    else:
        yield box["result"], _storage_html(), _dock_hidden(), _file_rows()


def _saved_ok(dest: Path) -> str:
    size = dest.stat().st_size if dest.is_file() else 0
    return _ok(f"Saved <span class='mono'>{html.escape(dest.name)}</span> "
               f"({human_size(size)})<br><span class='mono'>"
               f"{html.escape(str(dest))}</span>")


def handle_direct(url, filename, subfolder):
    if not url or not url.strip():
        yield _err("Paste a direct download link first."), _storage_html(), \
            _dock_hidden(), _file_rows()
        return
    label = f"Downloading {(filename or url).strip()[:60]}"

    def worker(st: _LiveProgress):
        dest = download_direct(url, custom_filename=filename or "",
                               subfolder=subfolder or "", progress=st.cb)
        return _saved_ok(dest)

    yield from _run_with_dock(label, worker)


def handle_youtube(url, quality, subfolder):
    if not url or not url.strip():
        yield _err("Paste a YouTube / video link first."), _storage_html(), \
            _dock_hidden(), _file_rows()
        return
    label = f"Downloading video {url.strip()[:60]}"

    def worker(st: _LiveProgress):
        dest = download_youtube(url, quality=quality, subfolder=subfolder or "",
                                progress=st.cb)
        return _saved_ok(dest)

    yield from _run_with_dock(label, worker)


def handle_gdrive(url, subfolder):
    if not url or not url.strip():
        yield _err("Paste a Google Drive shared link first (Anyone with the link)."), \
            _storage_html(), _dock_hidden(), _file_rows()
        return
    folder = is_gdrive_folder(url.strip())
    label = ("Cloning Drive folder" if folder else
             f"Saving shared file {url.strip()[:60]}")

    def worker(st: _LiveProgress):
        if folder:
            st.cb(0, 0, "Drive folder (no per-file progress)")
        dest = download_gdrive_shared(url, subfolder=subfolder or "",
                                      progress=st.cb)
        if dest.is_file():
            return _saved_ok(dest)
        return _ok(f"Folder saved: <span class='mono'>"
                   f"{html.escape(str(dest))}</span>")

    yield from _run_with_dock(label, worker)


def handle_bulk(text, subfolder):
    lines = [l.strip() for l in (text or "").splitlines() if l.strip()]
    if not lines:
        yield _err("Paste one URL per line first."), _storage_html(), \
            _dock_hidden(), _file_rows()
        return
    n = len(lines)

    def worker(st: _LiveProgress):
        results = []
        for i, url in enumerate(lines, 1):
            st.set_label(f"[{i}/{n}] {url[:50]}")
            kind = detect_link_type(url)
            try:
                if kind == "gdrive":
                    d = download_gdrive_shared(url, subfolder=subfolder or "",
                                               progress=st.cb)
                elif kind == "youtube":
                    d = download_youtube(url, subfolder=subfolder or "",
                                         progress=st.cb)
                else:
                    d = download_direct(url, subfolder=subfolder or "",
                                        progress=st.cb)
                results.append(f"✅ [{kind}] {html.escape(Path(d).name)}")
            except Exception as e:
                results.append(f"❌ {html.escape(url[:70])} — "
                               f"{html.escape(str(e)[:200])}")
        ok_count = sum(1 for r in results if r.startswith("✅"))
        return (f'<div class="result-ok">{ok_count}/{n} done<br>'
                f'{"<br>".join(results)}</div>')

    yield from _run_with_dock(f"Batch download ({n} links)", worker)


def refresh_files():
    rows = list_downloads()
    if not rows:
        return [], _storage_html()
    data = [[r["name"], r["size_h"]] for r in rows]
    return data, _storage_html()


def build_demo() -> gr.Blocks:
    # NOTE (Gradio 6): css/theme/js/head belong on launch(), not Blocks().
    # Passing them to Blocks() is ignored with a deprecation warning.
    with gr.Blocks(title="DriveFetch — Save to Drive") as demo:
        gr.HTML(f"""
        <div class="hero">
          <div class="hero-main">
            <div class="logo">DF</div>
            <div style="min-width:0">
              <h1>{APP_TITLE}<span class="version-pill">v1.3</span></h1>
              <p>{APP_SUB}. Files land directly in Drive — no Colab disk fill-ups, resumable, with live progress.</p>
              <div class="badges">
                <span class="badge dot b-green">Direct HTTP</span>
                <span class="badge dot b-blue">YouTube + 1000 sites</span>
                <span class="badge dot b-purple">Drive shared links</span>
                <span class="badge">⚡ Bulk mode</span>
                <span class="badge">🔒 Private — runs in your Colab</span>
              </div>
            </div>
          </div>
          <div class="theme-box">
            <label class="switch" title="Toggle dark / light">
              <input type="checkbox" id="df-theme-toggle" checked>
              <span class="slider"></span>
            </label>
            <small>DARK / LIGHT</small>
          </div>
        </div>
        """)

        storage = gr.HTML(_storage_html())

        # Components are created here; event wiring happens after the dock
        # exists (all outputs must exist before .click() references them).
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

                with gr.Tab("▶ YouTube / Video"):
                    gr.Markdown("YouTube, TikTok, Instagram, X, Facebook, Twitch, Vimeo + 1000 sites via yt-dlp.")
                    y_url = gr.Textbox(label="Video / playlist URL", placeholder="https://youtube.com/watch?v=…")
                    with gr.Row():
                        y_q = gr.Dropdown(list(YOUTUBE_QUALITY_MAP.keys()),
                                          value="Best (up to 1080p)", label="Quality")
                        y_folder = gr.Textbox(label="Subfolder (optional)", placeholder="videos")
                    y_btn = gr.Button("⬇ Download Video", variant="primary")
                    y_out = gr.HTML()

                with gr.Tab("📁 Drive Shared Link"):
                    gr.Markdown("Paste a **Anyone with the link** Google Drive file/folder link. Folders are cloned recursively.")
                    g_url = gr.Textbox(label="Shared link", placeholder="https://drive.google.com/file/d/…/view?usp=sharing")
                    g_folder = gr.Textbox(label="Subfolder (optional)", placeholder="shared")
                    g_btn = gr.Button("⬇ Save to My Drive", variant="primary")
                    g_out = gr.HTML()

                with gr.Tab("⚡ Bulk"):
                    gr.Markdown("One URL per line. Auto-detects Direct / Video / Drive links.")
                    b_text = gr.Textbox(label="URLs (one per line)", lines=6,
                                        placeholder="https://example.com/a.zip\nhttps://youtube.com/watch?v=…\nhttps://drive.google.com/file/d/…")
                    b_folder = gr.Textbox(label="Subfolder (optional)", placeholder="batch-01")
                    b_btn = gr.Button("⬇ Download All", variant="primary")
                    b_out = gr.HTML()

                with gr.Tab("📂 Files"):
                    gr.Markdown(f"Contents of `{get_download_root()}` (newest first).")
                    f_btn = gr.Button("🔄 Refresh")
                    f_table = gr.Dataframe(headers=["File", "Size"], datatype=["str", "str"],
                                           interactive=False, wrap=True)
                    f_btn.click(refresh_files, None, [f_table, storage])
                    demo.load(refresh_files, None, [f_table, storage])

        # Persistent bottom-docked status: hidden until a download starts.
        # Every download streams (result, storage, dock, files) tuples.
        dock = gr.HTML(_dock_hidden())
        d_btn.click(handle_direct, [d_url, d_name, d_folder],
                    [d_out, storage, dock, f_table])
        y_btn.click(handle_youtube, [y_url, y_q, y_folder],
                    [y_out, storage, dock, f_table])
        g_btn.click(handle_gdrive, [g_url, g_folder],
                    [g_out, storage, dock, f_table])
        b_btn.click(handle_bulk, [b_text, b_folder],
                    [b_out, storage, dock, f_table])

        gr.HTML('<div class="footer">DriveFetch • Colab + Local • yt-dlp • gdown • Gradio &nbsp;—&nbsp; only download content you have rights to.</div>')

    return demo


demo = build_demo()

if __name__ == "__main__":
    import os
    in_colab = os.path.exists("/content") or os.path.exists("/content/drive")
    demo.launch(share=in_colab, server_name="0.0.0.0", server_port=7860,
                theme=gr.themes.Soft(primary_hue="indigo"),
                css=CUSTOM_CSS, js=THEME_JS)
