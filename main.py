#!/usr/bin/env python3
"""
main.py (final patched)

- Timestamped folders: DOWNLOADER_OUT/YYYYmmdd_HHMMSS_<SHORTCODE>/
- Files renamed to ordered names: 01.ext, 02.ext, ...
- Non-media files (txt/json/etc.) moved to the end so 01.. are media files.
- Robust image detection using Pillow (looks_like_image).
- Compose first image (no crop) into template and atomically replace 01.* (if image).
- Clean logging.
"""

import os
import time
import shlex
import subprocess
import getpass
import logging
import platform
from datetime import datetime
from urllib.parse import urlparse
from typing import Optional, List, Tuple

# third-party
import instaloader
from instaloader import Instaloader, Post
from instaloader.exceptions import (
    ConnectionException,
    QueryReturnedNotFoundException,
    LoginRequiredException,
)
from PIL import Image, ExifTags

# ---------- CONFIG ----------
SESSION_DIR = ".sessions"
DELAY_BETWEEN_ACTIONS = 2
MAX_RETRIES = 4
YT_DLP_OPTS = "-f best"
# template fallback (file you uploaded earlier; change if you want another)
DEFAULT_TEMPLATE = "imgTemplate/repost - 2025-10-31T134140.153(1).png"

# cover placement (absolute)
COVER_W, COVER_H = 849, 1061
POS_X, POS_Y = 109, 137

IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".heic")
VIDEO_EXTS = (".mp4", ".mov", ".mkv", ".webm", ".avi")

# ---------- determine system Downloads folder ----------
def get_system_downloads_folder() -> str:
    system = platform.system()
    home = os.path.expanduser("~")
    try:
        if system == "Windows":
            user_profile = os.environ.get("USERPROFILE") or home
            downloads = os.path.join(user_profile, "Downloads")
        else:
            downloads = os.path.join(home, "Downloads")
        os.makedirs(downloads, exist_ok=True)
        if os.path.isdir(downloads) and os.access(downloads, os.W_OK):
            return downloads
    except Exception:
        pass
    return os.getcwd()

DOWNLOADS_ROOT = get_system_downloads_folder()
DOWNLOADER_OUT = os.path.join(DOWNLOADS_ROOT, "IG DOWNLOADS")
os.makedirs(SESSION_DIR, exist_ok=True)
os.makedirs(DOWNLOADER_OUT, exist_ok=True)

# ---------- Logging ----------
LOGFMT = "%(message)s"
logging.basicConfig(format=LOGFMT, level=logging.INFO)
logger = logging.getLogger("igdwnld")
logging.getLogger("instaloader").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("yt_dlp").setLevel(logging.WARNING)

# ---------- Helpers ----------
def parse_input(s: str):
    if not s:
        return None
    s = s.strip()
    if s.startswith("http://") or s.startswith("https://") or s.startswith("www."):
        parsed = urlparse(s if s.startswith("http") else "https://" + s)
        parts = [p for p in parsed.path.split("/") if p]
        if not parts:
            return None
        if parts[0] in ("p", "reel", "tv") and len(parts) >= 2:
            return (parts[0], parts[1])
        if len(parts) == 1:
            return ("profile", parts[0])
        last = parts[-1]
        if len(last) >= 6 and last.isalnum():
            return ("post", last)
        return None
    else:
        return ("profile", s)


def ensure_session(L: Instaloader, login_user: str, force_interactive=False):
    if not login_user:
        return False
    session_file = os.path.join(SESSION_DIR, f"session-{login_user}")
    if not force_interactive:
        try:
            L.load_session_from_file(login_user, filename=session_file)
            logger.info("[session] loaded saved session")
            return True
        except FileNotFoundError:
            pass
    try:
        logger.info("[session] perform interactive login (check phone/console)")
        L.interactive_login(login_user)
        L.save_session_to_file(filename=session_file)
        logger.info("[session] logged in and session saved")
        return True
    except Exception as e:
        logger.warning(f"[session] login failed: {e}")
        try:
            if os.path.exists(session_file):
                os.remove(session_file)
        except Exception:
            pass
        return False


def yt_dlp_download(url: str, outdir: str):
    os.makedirs(outdir, exist_ok=True)
    safe = shlex.quote(url)
    out_template = os.path.join(outdir, "%(id)s.%(ext)s")
    cmd = f"yt-dlp {YT_DLP_OPTS} -o {shlex.quote(out_template)} {safe}"
    logger.info("[yt-dlp] fallback download (quiet)...")
    try:
        subprocess.run(cmd, shell=True, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        logger.warning(f"[yt-dlp] error: {e}")


def collect_all_files_recursive(folder: str) -> List[str]:
    collected = []
    for root, dirs, files in os.walk(folder):
        for f in files:
            if f.startswith("."):
                continue
            collected.append(os.path.join(root, f))
    return collected


def normalize_and_number_media_flat(folder: str) -> List[Tuple[str, str]]:
    """
    Move and rename all media files found under 'folder' (recursively) into folder root.
    Then rename to ordered names: 01.ext, 02.ext, ...
    Non-media (txt/json/etc.) are moved last so that 01.. are always media when possible.
    Returns list of tuples (new_path, old_path).
    """
    all_files = collect_all_files_recursive(folder)
    items = [f for f in all_files if os.path.isfile(f)]
    # filter only those under this folder
    items = [f for f in items if os.path.commonpath([os.path.abspath(f), os.path.abspath(folder)]) == os.path.abspath(folder)]
    items.sort()

    # split media and other files so media are numbered first
    media_items = [f for f in items if f.lower().endswith(IMAGE_EXTS) or f.lower().endswith(VIDEO_EXTS)]
    other_items = [f for f in items if f not in media_items]

    ordered_items = media_items + other_items

    mapping = []
    idx = 1
    for src in ordered_items:
        ext = os.path.splitext(src)[1].lower() or ".jpg"
        new_name = f"{idx:02d}{ext}"
        new_path = os.path.join(folder, new_name)
        try:
            if os.path.abspath(src) != os.path.abspath(new_path):
                if os.path.exists(new_path):
                    j = 1
                    base = f"{idx:02d}-{j}{ext}"
                    while os.path.exists(os.path.join(folder, base)):
                        j += 1
                        base = f"{idx:02d}-{j}{ext}"
                    new_path = os.path.join(folder, base)
                os.replace(src, new_path)
            mapping.append((new_path, src))
        except Exception as e:
            logger.warning(f"[organize] failed to move {src} -> {new_path}: {e}")
            continue
        idx += 1
    return mapping


def get_first_media_file(folder: str) -> Optional[str]:
    """
    Return first valid media file (image or video) based on sorted order.
    Skip text/metadata files (e.g. txt, json).
    """
    files = sorted(f for f in os.listdir(folder) if not f.startswith("."))
    if not files:
        return None

    for f in files:
        lower = f.lower()
        if lower.endswith(IMAGE_EXTS) or lower.endswith(VIDEO_EXTS):
            return os.path.join(folder, f)
    return None


def is_image_ext(path: str) -> bool:
    return path.lower().endswith(IMAGE_EXTS)


def is_video_ext(path: str) -> bool:
    return path.lower().endswith(VIDEO_EXTS)


def looks_like_image(path: str) -> bool:
    """
    More reliable image detection: try to open with PIL and verify.
    Returns True if PIL can open it as an image, False otherwise.
    """
    try:
        with Image.open(path) as im:
            im.verify()
        return True
    except Exception:
        return False


def fix_exif_orientation(img: Image.Image) -> Image.Image:
    try:
        exif = img._getexif()
    except Exception:
        exif = None
    if not exif:
        return img
    orientation_key = None
    for k, v in ExifTags.TAGS.items():
        if v == 'Orientation':
            orientation_key = k
            break
    if not orientation_key:
        return img
    orientation = exif.get(orientation_key)
    if orientation == 3:
        img = img.rotate(180, expand=True)
    elif orientation == 6:
        img = img.rotate(270, expand=True)
    elif orientation == 8:
        img = img.rotate(90, expand=True)
    return img


def compose_and_replace_first_flat(folder: str, template_path: str):
    """
    Compose cover from first media file (01.*) if it is an image (detected by trying to open it),
    otherwise skip compose. Replaces the first file atomically.
    """
    # find the first numbered file (01.*) AFTER normalization; but robustly prefer the first media file
    first_media = get_first_media_file(folder)
    if not first_media:
        logger.info("[compose] no media found to compose")
        return

    # We prefer the numbered 01.* as the file to replace; find the actual 01.* if exists
    candidates = sorted([f for f in os.listdir(folder) if f.startswith("01") and not f.startswith(".")])
    if candidates:
        first_file = os.path.join(folder, candidates[0])
        # if 01.* exists but is not a media file, and first_media is a media file, we'll replace first_media positionally:
        # But to preserve ordering, we'll replace the actual first numbered media filename (prefer 01.* if it's media)
        if not (first_file.lower().endswith(IMAGE_EXTS) or first_file.lower().endswith(VIDEO_EXTS)):
            # prefer the first_media (which is media)
            first_file = first_media
    else:
        # no 01.* present (unlikely), fallback to first_media
        first_file = first_media

    if not os.path.exists(first_file):
        logger.info(f"[compose] first file missing: {first_file}")
        return

    # robust detection
    if not looks_like_image(first_file):
        logger.info(f"[compose] first media is not an image (skipping compose): {os.path.basename(first_file)}")
        return

    # template fallback if missing
    if not os.path.exists(template_path):
        logger.warning(f"[compose] template not found: {template_path}. Trying fallback default.")
        template_path = DEFAULT_TEMPLATE
        if not os.path.exists(template_path):
            logger.error("[compose] no template available; skipping compose")
            return

    try:
        tpl = Image.open(template_path).convert("RGBA")
    except Exception as e:
        logger.error(f"[compose] failed to open template: {e}")
        return

    try:
        src = Image.open(first_file).convert("RGBA")
    except Exception as e:
        logger.error(f"[compose] failed to open source image: {e}")
        return

    src = fix_exif_orientation(src)
    resized = src.resize((COVER_W, COVER_H), resample=Image.LANCZOS)
    composite = tpl.copy()
    composite.paste(resized, (POS_X, POS_Y), resized)

    tmp_path = os.path.join(folder, f"01.__tmp{os.path.splitext(first_file)[1]}")
    composite.convert("RGB").save(tmp_path, quality=90)
    try:
        os.replace(tmp_path, first_file)
        logger.info(f"[compose] composed and replaced {os.path.basename(first_file)}")
    except Exception as e:
        logger.error(f"[compose] replace failed: {e}")
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


# ---------- Download behavior ----------
def make_timestamped_target(shortcode: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    foldername = f"{ts}_{shortcode}"
    return foldername


def download_post_with_retries(L: Instaloader, shortcode: str, url_fallback: Optional[str] = None, template_path: Optional[str] = None):
    template_path = template_path or DEFAULT_TEMPLATE
    for attempt in range(MAX_RETRIES):
        try:
            post = Post.from_shortcode(L.context, shortcode)
            timestmp_name = make_timestamped_target(shortcode)
            target = timestmp_name
            L.dirname_pattern = os.path.join(DOWNLOADER_OUT, "{target}")
            L.download_post(post, target=target)
            dest_folder = os.path.join(DOWNLOADER_OUT, target)
            logger.info(f"[done] downloaded -> {dest_folder}")

            # normalize and number (media first)
            mapping = normalize_and_number_media_flat(dest_folder)
            if mapping:
                logger.info(f"[organize] moved and numbered {len(mapping)} file(s) in {dest_folder}")
            else:
                logger.info("[organize] no media files found after download")

            # find first media (robust)
            first_path = get_first_media_file(dest_folder)
            if first_path:
                if looks_like_image(first_path):
                    logger.info(f"[compose] composing cover from {os.path.basename(first_path)}")
                    compose_and_replace_first_flat(dest_folder, template_path)
                else:
                    logger.info("[compose] first media is not an image -> skipping compose")
            else:
                logger.info("[compose] no media for compose")
            return True
        except QueryReturnedNotFoundException:
            logger.error("[err] shortcode not found")
            return False
        except LoginRequiredException:
            logger.error("[err] login required for this post")
            if url_fallback:
                yt_dlp_download(url_fallback, DOWNLOADER_OUT)
                candidates = [d for d in os.listdir(DOWNLOADER_OUT) if shortcode in d]
                for cand in candidates:
                    cand_folder = os.path.join(DOWNLOADER_OUT, cand)
                    normalize_and_number_media_flat(cand_folder)
                    compose_and_replace_first_flat(cand_folder, template_path)
            return False
        except ConnectionException as e:
            backoff = 2 ** attempt
            logger.warning(f"[retry] connection issue: backing off {backoff}s")
            time.sleep(backoff)
            continue
        except Exception as e:
            logger.error(f"[err] unexpected: {e}")
            if url_fallback:
                yt_dlp_download(url_fallback, DOWNLOADER_OUT)
            return False
    logger.error("[err] exhausted retries")
    return False


def download_profile_with_retries(L: Instaloader, username: str):
    for attempt in range(MAX_RETRIES):
        try:
            timestmp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target = f"{timestmp}_profile_{username}"
            L.dirname_pattern = os.path.join(DOWNLOADER_OUT, "{target}")
            L.download_profile(username, profile_pic=False, download_stories=False, fast_update=True)
            dest_folder = os.path.join(DOWNLOADER_OUT, target)
            logger.info(f"[done] profile downloaded -> {dest_folder}")
            normalize_and_number_media_flat(dest_folder)
            return True
        except QueryReturnedNotFoundException:
            logger.error("[err] username not found")
            return False
        except LoginRequiredException:
            logger.error("[err] login required for profile")
            return False
        except ConnectionException as e:
            backoff = 2 ** attempt
            logger.warning(f"[retry] connection issue: backing off {backoff}s")
            time.sleep(backoff)
            continue
        except Exception as e:
            logger.error(f"[err] profile download failed: {e}")
            return False
    logger.error("[err] exhausted retries for profile")
    return False


# ---------- Main ----------
def main():
    L = Instaloader(download_comments=False, save_metadata=False)
    logger.info(f"=== IG downloader (tidy) — saving to: {DOWNLOADER_OUT} ===")
    login_user = input("Login username (enter to skip): ").strip()
    if login_user:
        choice = input("Force interactive login now? (y/N): ").strip().lower()
        force = choice == "y"
        ok = ensure_session(L, login_user, force_interactive=force)
        if not ok:
            logger.warning("[note] proceeding without logged-in session (private posts may fail)")

    try:
        while True:
            target = input("\nEnter post/reel/profile or username (blank to exit): ").strip()
            if not target:
                logger.info("Exit.")
                break
            parsed = parse_input(target)
            if not parsed:
                logger.warning("[input] not recognized. Example: https://www.instagram.com/p/SHORTCODE/ or username")
                continue
            kind, value = parsed
            time.sleep(DELAY_BETWEEN_ACTIONS)
            if kind in ("p", "post", "reel", "tv"):
                shortcode = value
                url_fb = None
                if kind == "reel":
                    url_fb = f"https://www.instagram.com/reel/{shortcode}/"
                elif kind == "tv":
                    url_fb = f"https://www.instagram.com/tv/{shortcode}/"
                else:
                    url_fb = f"https://www.instagram.com/p/{shortcode}/"
                logger.info(f"[task] detected {kind} {shortcode} -> downloading...")
                download_post_with_retries(L, shortcode, url_fallback=url_fb, template_path=DEFAULT_TEMPLATE)
            elif kind == "profile":
                logger.info(f"[task] downloading profile {value} ...")
                download_profile_with_retries(L, value)
            else:
                logger.warning("[input] unknown kind")
            time.sleep(DELAY_BETWEEN_ACTIONS)
            logger.info("[done] operation complete")
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user. Exiting.")
    except Exception as e:
        logger.error(f"[fatal] {e}")


if __name__ == "__main__":
    main()
