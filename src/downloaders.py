"""Core download engines for DriveFetch.

Supports:
 1. Direct HTTP(S) links (streamed, resumable, progress callback)
 2. YouTube / 1000+ sites via yt-dlp
 3. Google Drive shared links via gdown (file + folder)

Designed to work both in Google Colab (saves to /content/drive/MyDrive)
and locally (saves to ./downloads).
"""

from __future__ import annotations

import os
import re
import shutil
import urllib.parse
from pathlib import Path
from typing import Callable, Optional

import requests

ProgressFn = Optional[Callable[[int, int, str], None]]

COLAB_DRIVE_ROOT = Path("/content/drive/MyDrive")
LOCAL_DEFAULT = Path(__file__).resolve().parent.parent / "downloads"


def get_download_root() -> Path:
    """Return best download root: Drive in Colab, else local ./downloads."""
    if COLAB_DRIVE_ROOT.exists():
        root = COLAB_DRIVE_ROOT / "Downloads"
    else:
        root = LOCAL_DEFAULT
    root.mkdir(parents=True, exist_ok=True)
    return root


def resolve_dest(subfolder: str = "", filename: str = "") -> Path:
    root = get_download_root()
    if subfolder:
        # sanitize + block path traversal (.., absolute paths)
        safe = re.sub(r"[^\w\-./ ]", "_", subfolder).strip().strip("/")
        parts = [p for p in safe.split("/") if p not in ("", ".", "..")]
        for p in parts:
            root = root / p
    root.mkdir(parents=True, exist_ok=True)
    if filename:
        return root / Path(filename).name
    return root


def human_size(n: int) -> str:
    if not n:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    f = float(n)
    while f >= 1024 and i < len(units) - 1:
        f /= 1024
        i += 1
    return f"{f:.2f} {units[i]}"


def drive_storage() -> dict:
    root = get_download_root()
    try:
        total, used, free = shutil.disk_usage(root)
        return {
            "root": str(root),
            "total": total,
            "used": used,
            "free": free,
            "total_h": human_size(total),
            "used_h": human_size(used),
            "free_h": human_size(free),
        }
    except Exception:
        return {"root": str(root), "total": 0, "used": 0, "free": 0,
                "total_h": "?", "used_h": "?", "free_h": "?"}


def guess_filename(url: str, response: requests.Response | None = None) -> str:
    # 1. Content-Disposition
    if response is not None:
        cd = response.headers.get("content-disposition", "")
        m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)"?', cd)
        if m:
            name = urllib.parse.unquote(m.group(1).strip())
            if name:
                return name
    # 2. URL path
    path = urllib.parse.urlparse(url).path
    name = os.path.basename(path)
    name = urllib.parse.unquote(name)
    if name and "." in name:
        return name
    return "download.bin"


def download_direct(
    url: str,
    custom_filename: str = "",
    subfolder: str = "",
    progress: ProgressFn = None,
    chunk_size: int = 1024 * 256,
) -> Path:
    """Download a direct HTTP(S) file straight to Drive/downloads with progress."""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        raise ValueError("URL must start with http:// or https://")

    headers = {"User-Agent": "Mozilla/5.0 (DriveFetch/1.0)"}
    with requests.get(url, stream=True, headers=headers, timeout=30) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        filename = custom_filename.strip() or guess_filename(url, r)
        dest = resolve_dest(subfolder, filename)

        # resume support
        downloaded = 0
        mode = "wb"
        if dest.exists():
            downloaded = dest.stat().st_size
            if total and downloaded < total:
                headers["Range"] = f"bytes={downloaded}-"
                # re-request with range — simplify: restart ranged request
                r.close()
                rr = requests.get(url, stream=True, headers=headers, timeout=30)
                rr.raise_for_status()
                if rr.status_code == 206:
                    mode = "ab"
                    r = rr
                else:
                    downloaded = 0
                    mode = "wb"
                    r = rr
            elif total and downloaded >= total:
                if progress:
                    progress(total, total, dest.name)
                return dest

        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, mode) as f:
            for chunk in r.iter_content(chunk_size=chunk_size):
                if not chunk:
                    continue
                f.write(chunk)
                downloaded += len(chunk)
                if progress:
                    progress(downloaded, total, dest.name)
    return dest


YOUTUBE_QUALITY_MAP = {
    "Best (up to 1080p)": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
    "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
    "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]/best",
    "Audio only (MP3)": "bestaudio/best",
}


def download_youtube(
    url: str,
    quality: str = "Best (up to 1080p)",
    subfolder: str = "",
    progress: ProgressFn = None,
) -> Path:
    """Download via yt-dlp. Supports YouTube + 1000 sites."""
    try:
        import yt_dlp
    except ImportError as e:
        raise RuntimeError("yt-dlp not installed. Run: pip install yt-dlp") from e

    url = url.strip()
    if not url:
        raise ValueError("Empty URL")

    dest_dir = resolve_dest(subfolder)
    audio_only = quality == "Audio only (MP3)"
    fmt = YOUTUBE_QUALITY_MAP.get(quality, YOUTUBE_QUALITY_MAP["Best (up to 1080p)"])

    downloaded_path: list[str] = []

    def hook(d):
        if progress:
            total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            done = d.get("downloaded_bytes", 0)
            fname = d.get("filename", "")
            progress(done, total, Path(fname).name if fname else "media")
        if d.get("status") == "finished":
            fn = d.get("filename")
            if fn:
                downloaded_path.append(fn)

    outtmpl = str(dest_dir / "%(title)s [%(id)s].%(ext)s")
    ydl_opts: dict = {
        "format": fmt,
        "outtmpl": outtmpl,
        "merge_output_format": "mp4",
        "noplaylist": False,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [hook],
    }
    if audio_only:
        ydl_opts.update({
            "format": "bestaudio/best",
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }],
        })

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

    if downloaded_path:
        p = Path(downloaded_path[-1])
        # mp3 conversion changes extension
        if audio_only and p.suffix != ".mp3":
            cand = p.with_suffix(".mp3")
            if cand.exists():
                return cand
        if p.exists():
            return p
    # fallback: newest file in dest dir
    files = sorted(dest_dir.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True)
    if files:
        return files[0]
    raise RuntimeError("yt-dlp finished but no file found.")


GDRIVE_ID_PATTERNS = [
    r"/file/d/([-\w]{25,})",
    r"id=([-\w]{25,})",
    r"/folders/([-\w]{25,})",
    r"^([-\w]{25,})$",
]


def extract_gdrive_id(url: str) -> Optional[str]:
    url = url.strip()
    for pat in GDRIVE_ID_PATTERNS:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None


def is_gdrive_folder(url: str) -> bool:
    return "/folders/" in url or "drive/folders" in url


def download_gdrive_shared(
    url: str,
    subfolder: str = "",
    progress: ProgressFn = None,
) -> Path:
    """Download a Google Drive shared file/folder link via gdown."""
    try:
        import gdown
    except ImportError as e:
        raise RuntimeError("gdown not installed. Run: pip install gdown") from e

    url = url.strip()
    if "drive.google.com" not in url and extract_gdrive_id(url) is None:
        # not a gdrive link — treat as direct
        return download_direct(url, subfolder=subfolder, progress=progress)

    dest_dir = resolve_dest(subfolder)
    if is_gdrive_folder(url):
        # folder download
        out = dest_dir / "gdrive_folder"
        out.mkdir(parents=True, exist_ok=True)
        gdown.download_folder(url, output=str(out), quiet=True, use_cookies=False)
        return out

    file_id = extract_gdrive_id(url)
    if not file_id:
        raise ValueError("Could not parse Google Drive file ID from link.")

    # probe filename via gdown? download then return path
    tmp_out = str(dest_dir / "temp_gdrive_download")
    downloaded = gdown.download(id=file_id, output=tmp_out, quiet=True, fuzzy=True)
    if not downloaded:
        raise RuntimeError("gdown failed. Is the link public? (Anyone with link)")
    p = Path(downloaded)
    # gdown may save without extension; keep as-is
    if progress:
        try:
            progress(p.stat().st_size, p.stat().st_size, p.name)
        except Exception:
            pass
    return p


def detect_link_type(url: str) -> str:
    u = url.lower()
    if "drive.google.com" in u or "/folders/" in u:
        return "gdrive"
    if any(d in u for d in ["youtube.com", "youtu.be", "tiktok.com",
                            "instagram.com", "twitter.com", "x.com",
                            "facebook.com", "twitch.tv", "vimeo.com",
                            "soundcloud.com", "reddit.com"]):
        return "youtube"
    return "direct"


def list_downloads(limit: int = 100) -> list[dict]:
    root = get_download_root()
    files = []
    for p in root.rglob("*"):
        if p.is_file():
            try:
                st = p.stat()
                files.append({
                    "name": str(p.relative_to(root)),
                    "size": st.st_size,
                    "size_h": human_size(st.st_size),
                    "mtime": st.st_mtime,
                })
            except Exception:
                continue
    files.sort(key=lambda x: x["mtime"], reverse=True)
    return files[:limit]
