"""
API routes - AJAX endpoints
"""
from flask import Blueprint, request, jsonify, current_app, session
import os
import threading
import time
import shutil
import platform
import subprocess
from app.services.instagram import IGDownloader

bp = Blueprint('api', __name__)

# Store active downloads (in production, use Redis or database)
active_downloads = {}


class DownloadThread(threading.Thread):
    """Background thread for downloading"""
    def __init__(self, task_id, downloader, download_type, value, session_id, add_cover=True, custom_caption=None):
        super().__init__()
        self.task_id = task_id
        self.downloader = downloader
        self.download_type = download_type
        self.value = value
        self.session_id = session_id
        self.add_cover = add_cover
        self.custom_caption = custom_caption
        self.result = None
    
    def progress_callback(self, progress, message):
        """Update progress"""
        if self.task_id in active_downloads:
            active_downloads[self.task_id]['progress'] = progress
            active_downloads[self.task_id]['message'] = message
    
    def run(self):
        """Execute download"""
        try:
            active_downloads[self.task_id]['status'] = 'downloading'
            
            if self.download_type in ('post', 'p', 'reel', 'tv'):
                self.result = self.downloader.download_post(self.value, self.progress_callback, self.add_cover, self.custom_caption)
            elif self.download_type == 'profile':
                self.result = self.downloader.download_profile(self.value, self.progress_callback)
            else:
                self.result = {'success': False, 'message': 'Invalid download type'}
            
            active_downloads[self.task_id]['status'] = 'completed' if self.result['success'] else 'failed'
            active_downloads[self.task_id]['result'] = self.result
            active_downloads[self.task_id]['progress'] = 100
            
        except Exception as e:
            active_downloads[self.task_id]['status'] = 'failed'
            active_downloads[self.task_id]['message'] = str(e)
            active_downloads[self.task_id]['progress'] = 0


@bp.route('/parse', methods=['POST'])
def parse_url():
    """Parse Instagram URL or username"""
    data = request.get_json()
    url_or_username = data.get('url', '').strip()
    
    if not url_or_username:
        return jsonify({'error': 'URL or username is required'}), 400
    
    downloader = IGDownloader(current_app.config)
    parsed = downloader.parse_input(url_or_username)
    
    if not parsed:
        return jsonify({'error': 'Invalid Instagram URL or username'}), 400
    
    kind, value = parsed
    
    response = {
        'type': kind,
        'value': value,
        'description': f"{'Post/Reel' if kind in ('p', 'post', 'reel', 'tv') else 'Profile'}: {value}"
    }
    
    # Get preview for posts/reels (with caption for repost)
    if kind in ('p', 'post', 'reel', 'tv'):
        preview = downloader.get_post_preview(value)
        if preview['success']:
            response['preview'] = preview
        elif preview['error']:
            response['preview_error'] = preview['error']
    
    return jsonify(response)
    
    # Get preview for posts/reels
    if kind in ('p', 'post', 'reel', 'tv'):
        preview = downloader.get_post_preview(value)
        if preview['success']:
            response['preview'] = preview
        elif preview['error']:
            response['preview_error'] = preview['error']
    
    return jsonify(response)


@bp.route('/download', methods=['POST'])
def start_download():
    """Start download task"""
    data = request.get_json()
    url_or_username = data.get('url', '').strip()
    add_cover = data.get('add_cover', True)  # Default True for cover creation
    custom_caption = data.get('custom_caption', None)  # Custom caption template (always generate caption)
    
    if not url_or_username:
        return jsonify({'error': 'URL or username is required'}), 400
    
    # Parse input
    downloader = IGDownloader(current_app.config)
    parsed = downloader.parse_input(url_or_username)
    
    if not parsed:
        return jsonify({'error': 'Invalid Instagram URL or username'}), 400
    
    kind, value = parsed
    
    # Store cover preference
    session['add_cover'] = add_cover
    
    # Generate task ID
    task_id = f"{int(time.time())}_{value}"
    
    # Initialize task status
    active_downloads[task_id] = {
        'status': 'pending',
        'progress': 0,
        'message': 'Initializing...',
        'result': None
    }
    
    # Start download in background
    thread = DownloadThread(task_id, downloader, kind, value, session.get('_id'), add_cover, custom_caption)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'task_id': task_id,
        'message': 'Download started',
        'type': kind,
        'value': value
    })


@bp.route('/status/<task_id>', methods=['GET'])
def check_status(task_id):
    """Check download status"""
    if task_id not in active_downloads:
        return jsonify({'error': 'Task not found'}), 404
    
    task = active_downloads[task_id]
    response = {
        'task_id': task_id,
        'status': task['status'],
        'progress': task['progress'],
        'message': task['message']
    }
    
    if task['status'] == 'completed' and task['result']:
        result = task['result']
        response['success'] = result['success']
        response['folder'] = os.path.basename(result.get('folder', '')) if result.get('folder') else None
        response['files'] = result.get('files', [])
        response['result_message'] = result.get('message', '')
        response['repost_caption'] = result.get('repost_caption')  # Include repost caption
    
    return jsonify(response)


@bp.route('/open-folder/<folder_name>', methods=['POST'])
def open_folder(folder_name):
    """Open folder in file manager"""
    import platform
    import subprocess
    
    download_folder = current_app.config['DOWNLOAD_FOLDER']
    folder_path = os.path.join(download_folder, folder_name)
    
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        return jsonify({'error': 'Folder not found'}), 404
    
    try:
        system = platform.system()
        if system == 'Darwin':  # macOS
            subprocess.run(['open', folder_path])
        elif system == 'Windows':
            subprocess.run(['explorer', folder_path])
        else:  # Linux
            subprocess.run(['xdg-open', folder_path])
        
        return jsonify({'success': True, 'message': 'Folder opened', 'path': folder_path})
    except Exception as e:
        return jsonify({'error': f'Failed to open folder: {str(e)}'}), 500


@bp.route('/delete-folder/<folder_name>', methods=['DELETE'])
def delete_folder(folder_name):
    """Delete downloaded folder"""
    download_folder = current_app.config['DOWNLOAD_FOLDER']
    folder_path = os.path.join(download_folder, folder_name)
    
    if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
        return jsonify({'error': 'Folder not found'}), 404
    
    try:
        shutil.rmtree(folder_path)
        return jsonify({'success': True, 'message': 'Folder deleted'})
    except Exception as e:
        return jsonify({'error': f'Failed to delete folder: {str(e)}'}), 500


@bp.route('/login', methods=['POST'])
def login():
    """Handle Instagram login"""
    data = request.get_json()
    username = data.get('username', '').strip()
    
    if not username:
        return jsonify({'error': 'Username is required'}), 400
    
    # For now, just acknowledge. Actual login requires interactive process
    # In production, you'd implement proper session management
    session['ig_username'] = username
    
    return jsonify({
        'success': True,
        'message': 'Login information saved. Note: Private posts may still require authentication.',
        'username': username
    })


@bp.route('/logout', methods=['POST'])
def logout():
    """Clear login session"""
    session.pop('ig_username', None)
    return jsonify({'success': True, 'message': 'Logged out'})
