"""
Twitter tools routes
"""
from flask import Blueprint, render_template, request, jsonify
from app.services.twitter import ThreadAdjuster

bp = Blueprint('twitter', __name__, url_prefix='/twitter')


@bp.route('/thread-adjuster')
def thread_adjuster():
    """Thread adjuster page"""
    return render_template('twitter/twitter_thread.html')


@bp.route('/api/adjust-thread', methods=['POST'])
def adjust_thread():
    """API endpoint to adjust text into threads"""
    data = request.get_json()
    text = data.get('text', '').strip()
    
    if not text:
        return jsonify({'error': 'Text is required'}), 400
    
    adjuster = ThreadAdjuster()
    result = adjuster.adjust_thread(text)
    
    return jsonify(result)
