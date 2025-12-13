"""
Configuration for Flask webapp
"""
import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Flask config
    DEBUG = False
    TESTING = False
    
    # Upload config
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max upload
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'uploads')
    # Download to user's Downloads folder (like CLI)
    DOWNLOAD_FOLDER = os.path.join(os.path.expanduser('~'), 'Downloads', 'IG DOWNLOADS')
    
    # Session config
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Instagram downloader config
    SESSION_DIR = ".sessions"
    DELAY_BETWEEN_ACTIONS = 2
    MAX_RETRIES = 4
    YT_DLP_OPTS = "-f best"
    DEFAULT_TEMPLATE = "app/static/images/coverTemplate.png"
    
    # Image composition config
    COVER_W = 849
    COVER_H = 1061
    POS_X = 109
    POS_Y = 137
    
    # File extensions
    IMAGE_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".heic")
    VIDEO_EXTS = (".mp4", ".mov", ".mkv", ".webm", ".avi")


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SESSION_COOKIE_SECURE = True


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
