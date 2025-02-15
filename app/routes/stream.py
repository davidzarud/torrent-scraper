import re

from flask import Blueprint, jsonify, request, send_file

from app.services.config import DOWNLOADS_BASE_PATH
from app.services.stream_service import find_media_files, stream_and_remux, stream_mp4
from app.services.utils import is_windows

stream_bp = Blueprint("stream", __name__, url_prefix="")


@stream_bp.route('/api/title-exists')
def title_exists():
    title = re.sub(r'[<>:"/\\|?*]', '', request.args.get('title'))
    context = request.args.get('context')
    season_episode = request.args.get('seasonEpisode')
    if is_windows:
        media_file_path = f'\\\\192.168.1.194\\data\\downloads\\{context}\\{title}'
    else:
        media_file_path = f'{DOWNLOADS_BASE_PATH}/{context}/{title}'

    # Get all media files and check if any exist
    media_files = find_media_files(media_file_path, context, season_episode)
    exists = len(media_files) > 0

    return jsonify({
        'exists': exists,
        'files': media_files  # Return the list of media files
    })


@stream_bp.route('/stream/<string:torrent_title>')
def stream(torrent_title):
    if request.args.get('file').lower().endswith(".mkv"):
        return stream_and_remux(torrent_title)
    elif request.args.get('file').lower().endswith(".mp4"):
        return stream_mp4(torrent_title)
    else:
        return "Bad file type", 400


@stream_bp.route('/subtitle')
def fetch_subtitles():
    subtitle_path = request.args.get('path')
    return send_file(subtitle_path, mimetype='text/vtt')