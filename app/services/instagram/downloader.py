"""
Instagram downloader service layer
Refactored from main.py to be used in web context
"""
import os
import time
import shlex
import subprocess
import logging
import platform
from datetime import datetime
from urllib.parse import urlparse
from typing import Optional, List, Tuple, Dict, Callable

import instaloader
from instaloader import Instaloader, Post
from instaloader.exceptions import (
    ConnectionException,
    QueryReturnedNotFoundException,
    LoginRequiredException,
)
from PIL import Image, ExifTags

logger = logging.getLogger(__name__)


class DownloadProgress:
    """Class to track download progress"""
    def __init__(self):
        self.status = "idle"
        self.message = ""
        self.progress = 0
        self.result_folder = None
        self.error = None


class IGDownloader:
    """Instagram downloader service"""
    
    def __init__(self, config):
        self.config = config
        self.session_dir = config['SESSION_DIR']
        self.downloads_root = config['DOWNLOAD_FOLDER']
        self.delay = config['DELAY_BETWEEN_ACTIONS']
        self.max_retries = config['MAX_RETRIES']
        self.template_path = config['DEFAULT_TEMPLATE']
        
        # Image composition config
        self.cover_w = config['COVER_W']
        self.cover_h = config['COVER_H']
        self.pos_x = config['POS_X']
        self.pos_y = config['POS_Y']
        
        # File extensions
        self.image_exts = config['IMAGE_EXTS']
        self.video_exts = config['VIDEO_EXTS']
        
        os.makedirs(self.session_dir, exist_ok=True)
        os.makedirs(self.downloads_root, exist_ok=True)
        
        # Initialize Instaloader
        self.loader = Instaloader(download_comments=False, save_metadata=False)
    
    def parse_input(self, s: str) -> Optional[Tuple[str, str]]:
        """Parse Instagram URL or username"""
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
    
    def get_post_preview(self, shortcode: str) -> Dict:
        """Get post preview info (thumbnail, caption, etc)"""
        result = {
            'success': False,
            'thumbnail_url': None,
            'caption': None,
            'owner': None,
            'likes': None,
            'comments': None,
            'is_video': False,
            'error': None
        }
        
        try:
            post = Post.from_shortcode(self.loader.context, shortcode)
            
            # Get thumbnail URL
            result['thumbnail_url'] = post.url
            
            # Get caption (first 200 chars)
            caption = post.caption or ""
            result['caption'] = caption[:300] + "..." if len(caption) > 300 else caption
            
            # Get metadata
            result['owner'] = post.owner_username
            result['likes'] = post.likes
            result['comments'] = post.comments
            result['is_video'] = post.is_video
            result['success'] = True
            
        except QueryReturnedNotFoundException:
            result['error'] = "Post not found"
        except LoginRequiredException:
            result['error'] = "Login required for this post"
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"[preview] error: {e}")
        
        return result
    
    def ensure_session(self, login_user: str, force_interactive=False) -> bool:
        """Load or create Instagram session"""
        if not login_user:
            return False
        session_file = os.path.join(self.session_dir, f"session-{login_user}")
        if not force_interactive:
            try:
                self.loader.load_session_from_file(login_user, filename=session_file)
                logger.info("[session] loaded saved session")
                return True
            except FileNotFoundError:
                pass
        try:
            logger.info("[session] perform interactive login")
            self.loader.interactive_login(login_user)
            self.loader.save_session_to_file(filename=session_file)
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
    
    def collect_all_files_recursive(self, folder: str) -> List[str]:
        """Collect all files recursively in folder"""
        collected = []
        for root, dirs, files in os.walk(folder):
            for f in files:
                if f.startswith("."):
                    continue
                collected.append(os.path.join(root, f))
        return collected
    
    def normalize_and_number_media_flat(self, folder: str) -> List[Tuple[str, str]]:
        """Move and rename all media files to numbered format"""
        all_files = self.collect_all_files_recursive(folder)
        items = [f for f in all_files if os.path.isfile(f)]
        items = [f for f in items if os.path.commonpath([os.path.abspath(f), os.path.abspath(folder)]) == os.path.abspath(folder)]
        items.sort()
        
        media_items = [f for f in items if f.lower().endswith(self.image_exts) or f.lower().endswith(self.video_exts)]
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
    
    def get_first_media_file(self, folder: str) -> Optional[str]:
        """Get first media file in folder"""
        files = sorted(f for f in os.listdir(folder) if not f.startswith("."))
        if not files:
            return None
        for f in files:
            lower = f.lower()
            if lower.endswith(self.image_exts) or lower.endswith(self.video_exts):
                return os.path.join(folder, f)
        return None
    
    def looks_like_image(self, path: str) -> bool:
        """Check if file is a valid image"""
        try:
            with Image.open(path) as im:
                im.verify()
            return True
        except Exception:
            return False
    
    def fix_exif_orientation(self, img: Image.Image) -> Image.Image:
        """Fix image orientation based on EXIF data"""
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
    
    def compose_cover_separate(self, folder: str, template_path: str = None):
        """Compose cover image with template and save separately as .cover file"""
        template_path = template_path or self.template_path
        first_media = self.get_first_media_file(folder)
        if not first_media:
            logger.info("[compose] no media found to compose")
            return
        
        candidates = sorted([f for f in os.listdir(folder) if f.startswith("01") and not f.startswith(".")])
        if candidates:
            first_file = os.path.join(folder, candidates[0])
            if not (first_file.lower().endswith(self.image_exts) or first_file.lower().endswith(self.video_exts)):
                first_file = first_media
        else:
            first_file = first_media
        
        if not os.path.exists(first_file):
            logger.info(f"[compose] first file missing: {first_file}")
            return
        
        if not self.looks_like_image(first_file):
            logger.info(f"[compose] first media is not an image (skipping compose): {os.path.basename(first_file)}")
            return
        
        if not os.path.exists(template_path):
            logger.warning(f"[compose] template not found: {template_path}")
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
        
        src = self.fix_exif_orientation(src)
        resized = src.resize((self.cover_w, self.cover_h), resample=Image.LANCZOS)
        composite = tpl.copy()
        composite.paste(resized, (self.pos_x, self.pos_y), resized)
        
        # Save as separate .cover file instead of replacing
        base_name = os.path.splitext(first_file)[0]
        cover_path = f"{base_name}.cover.jpg"
        
        try:
            composite.convert("RGB").save(cover_path, quality=90)
            logger.info(f"[compose] created cover: {os.path.basename(cover_path)}")
        except Exception as e:
            logger.error(f"[compose] save cover failed: {e}")
    
    def create_repost_caption(self, username: str, original_caption: str = "", custom_template: str = None) -> str:
        """Create repost caption with custom template or default #Repost from @username
        
        Args:
            username: Instagram username
            original_caption: Original post caption
            custom_template: Custom template. If None, use default. If empty string "", use only original caption.
        """
        # If custom_template is explicitly set (not None), use it
        if custom_template is not None:
            # If template is empty string, return only original caption
            if custom_template.strip() == "":
                return original_caption
            
            # Replace @username with actual username
            caption = custom_template.replace('@username', f'@{username}')
            # Add original caption if exists
            if original_caption:
                caption = f"{caption}{original_caption}"
            return caption
        
        # Default template (when custom_template is None)
        repost_text = f"#Repost from @{username}"
        if original_caption:
            return f"{repost_text}\n\n{original_caption}"
        return repost_text
    
    def make_timestamped_target(self, shortcode: str) -> str:
        """Generate timestamped folder name"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{ts}_{shortcode}"
    
    def download_post(self, shortcode: str, progress_callback: Optional[Callable] = None, add_cover: bool = True, custom_caption: str = None) -> Dict:
        """Download Instagram post with progress tracking
        
        Args:
            shortcode: Instagram post shortcode
            progress_callback: Callback for progress updates
            add_cover: Whether to create cover image (default True)
            custom_caption: Custom caption template (always generates caption)
        """
        result = {
            'success': False,
            'folder': None,
            'message': '',
            'files': [],
            'repost_caption': None
        }
        
        if progress_callback:
            progress_callback(10, "Fetching post data...")
        
        for attempt in range(self.max_retries):
            try:
                post = Post.from_shortcode(self.loader.context, shortcode)
                
                # Get caption and username for repost
                username = post.owner_username
                caption = post.caption or ""
                
                if progress_callback:
                    progress_callback(30, "Downloading media files...")
                
                timestmp_name = self.make_timestamped_target(shortcode)
                target = timestmp_name
                self.loader.dirname_pattern = os.path.join(self.downloads_root, "{target}")
                self.loader.download_post(post, target=target)
                dest_folder = os.path.join(self.downloads_root, target)
                
                if progress_callback:
                    progress_callback(60, "Organizing files...")
                
                mapping = self.normalize_and_number_media_flat(dest_folder)
                
                if progress_callback:
                    progress_callback(80, "Creating cover image..." if add_cover else "Finalizing...")
                
                # Create cover as separate file (only if add_cover=True)
                if add_cover:
                    first_path = self.get_first_media_file(dest_folder)
                    if first_path and self.looks_like_image(first_path):
                        self.compose_cover_separate(dest_folder, self.template_path)
                
                # Always create repost caption (regardless of cover)
                repost_caption = self.create_repost_caption(username, caption, custom_caption)
                result['repost_caption'] = repost_caption
                
                # Save caption to file
                caption_file = os.path.join(dest_folder, "caption.txt")
                with open(caption_file, 'w', encoding='utf-8') as f:
                    f.write(repost_caption)
                logger.info(f"[caption] saved repost caption to {caption_file}")
                
                # Get list of files
                files = sorted([f for f in os.listdir(dest_folder) if not f.startswith(".")])
                
                if progress_callback:
                    progress_callback(100, "Download completed!")
                
                result['success'] = True
                result['folder'] = dest_folder
                result['message'] = f"Successfully downloaded {len(files)} file(s)"
                result['files'] = files
                return result
                
            except QueryReturnedNotFoundException:
                result['message'] = "Post not found. Check the URL/shortcode."
                return result
            except LoginRequiredException:
                result['message'] = "Login required for this post. Please login first."
                return result
            except ConnectionException as e:
                backoff = 2 ** attempt
                if progress_callback:
                    progress_callback(20 + attempt * 10, f"Connection issue, retrying in {backoff}s...")
                logger.warning(f"[retry] connection issue: backing off {backoff}s")
                time.sleep(backoff)
                continue
            except Exception as e:
                result['message'] = f"Error: {str(e)}"
                logger.error(f"[err] unexpected: {e}")
                return result
        
        result['message'] = "Failed after maximum retries. Please try again later."
        return result
    
    def download_profile(self, username: str, progress_callback: Optional[Callable] = None) -> Dict:
        """Download Instagram profile posts"""
        result = {
            'success': False,
            'folder': None,
            'message': '',
            'files': []
        }
        
        if progress_callback:
            progress_callback(10, "Connecting to Instagram...")
        
        for attempt in range(self.max_retries):
            try:
                timestmp = datetime.now().strftime("%Y%m%d_%H%M%S")
                target = f"{timestmp}_profile_{username}"
                self.loader.dirname_pattern = os.path.join(self.downloads_root, "{target}")
                
                if progress_callback:
                    progress_callback(30, f"Downloading profile @{username}...")
                
                self.loader.download_profile(username, profile_pic=False, download_stories=False, fast_update=True)
                dest_folder = os.path.join(self.downloads_root, target)
                
                if progress_callback:
                    progress_callback(80, "Organizing files...")
                
                self.normalize_and_number_media_flat(dest_folder)
                
                files = sorted([f for f in os.listdir(dest_folder) if not f.startswith(".")])
                
                if progress_callback:
                    progress_callback(100, "Profile download completed!")
                
                result['success'] = True
                result['folder'] = dest_folder
                result['message'] = f"Successfully downloaded profile with {len(files)} file(s)"
                result['files'] = files
                return result
                
            except QueryReturnedNotFoundException:
                result['message'] = f"Username @{username} not found."
                return result
            except LoginRequiredException:
                result['message'] = "Login required for this profile. Please login first."
                return result
            except ConnectionException as e:
                backoff = 2 ** attempt
                if progress_callback:
                    progress_callback(20 + attempt * 10, f"Connection issue, retrying in {backoff}s...")
                logger.warning(f"[retry] connection issue: backing off {backoff}s")
                time.sleep(backoff)
                continue
            except Exception as e:
                result['message'] = f"Error downloading profile: {str(e)}"
                logger.error(f"[err] profile download failed: {e}")
                return result
        
        result['message'] = "Failed after maximum retries. Please try again later."
        return result
