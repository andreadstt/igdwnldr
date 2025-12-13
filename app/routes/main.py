"""
Main routes - UI pages
"""
from flask import Blueprint, render_template, session, current_app
import os

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    """Home page - Tools directory"""
    return render_template('home.html')


@bp.route('/ig-reposter')
def ig_reposter():
    """Instagram Reposter tool"""
    return render_template('instagram/ig_reposter.html')


@bp.route('/downloads')
def downloads():
    """List of downloaded items"""
    download_folder = current_app.config['DOWNLOAD_FOLDER']
    
    # Get list of folders in downloads
    folders = []
    if os.path.exists(download_folder):
        for item in sorted(os.listdir(download_folder), reverse=True):
            item_path = os.path.join(download_folder, item)
            if os.path.isdir(item_path):
                # Get file count
                files = [f for f in os.listdir(item_path) if not f.startswith('.')]
                folders.append({
                    'name': item,
                    'file_count': len(files),
                    'path': item_path
                })
    
    return render_template('downloads.html', folders=folders)
