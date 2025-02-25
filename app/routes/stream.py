import logging
import os
import re
import subprocess

from flask import Blueprint, jsonify, request, send_file, Response, redirect, url_for

from app.services.config import DOWNLOADS_BASE_PATH, DASH_OUTPUT_DIR
from app.services.stream_service import find_media_files, stream_mp4, process_mkv_to_dash
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
    file_param = request.args.get('file')
    if not file_param or not os.path.exists(file_param):
        logging.error("Invalid or missing file parameter")
        return "File not found", 404

    base_dir = os.path.dirname(file_param)  # Extract directory
    output_dir = os.path.join(base_dir, "dash")
    os.makedirs(output_dir, exist_ok=True)

    manifest_path = os.path.join(output_dir, "manifest.mpd")

    # Generate DASH files if not present
    if not os.path.exists(manifest_path):
        ffmpeg_command = [
            "ffmpeg", "-i", file_param,
            "-map", "0:v:0", "-map", "0:a:m:language:eng",
            "-c:v", "copy", "-c:a", "aac",
            "-b:a", "192k", "-preset", "ultrafast",
            "-f", "dash",
            "-seg_duration", "4",
            "-use_timeline", "1",
            "-use_template", "1",
            os.path.join(output_dir, "manifest.mpd")
        ]
        try:
            subprocess.run(ffmpeg_command, check=True)
            logging.info("DASH segments created successfully")
        except subprocess.CalledProcessError as e:
            logging.error(f"FFmpeg failed: {e}")
            return "Error generating DASH stream", 500

    return send_from_directory(output_dir, "manifest.mpd")


@stream_bp.route('/subtitle')
def fetch_subtitles():
    subtitle_path = request.args.get('path')
    return send_file(subtitle_path, mimetype='text/vtt')


def stream_and_remux(torrent_title):
    """
    Processes an MKV file for DASH output.
    The 'file' query parameter is a full file path. We extract the directory
    by omitting everything after the last '/' (if needed) and then process the file.
    """
    # Here, file_param is expected to be a full file path.
    media_file_path = request.args.get('file')
    if not os.path.exists(media_file_path):
        logging.error("Torrent file not found: %s", media_file_path)
        return Response("File not found", status=404)

    # Optionally, extract the torrent directory:
    torrent_dir = os.path.dirname(media_file_path)
    logging.info("Torrent file directory: %s", torrent_dir)

    # Process the MKV file into DASH (the torrent_title should ideally match the torrent directory name).
    mpd_file = process_mkv_to_dash(torrent_title, media_file_path, torrent_dir)
    if not mpd_file:
        return Response("Error processing file", status=500)

    # Redirect the client to the DASH manifest endpoint.
    return redirect(url_for('stream.dash_manifest', torrent_title=torrent_title, torrent_dir=torrent_dir))


@stream_bp.route('/dash/<string:torrent_title>/<string:torrent_dir>/manifest.mpd')
def dash_manifest(torrent_title, torrent_dir):
    """
    Serves the DASH manifest (MPD file) for the given torrent title.
    """
    mpd_file = os.path.join(torrent_dir, DASH_OUTPUT_DIR, "manifest.mpd")
    if os.path.exists(mpd_file):
        return send_file(mpd_file, mimetype='application/dash+xml')
    else:
        return Response("DASH manifest not found", status=404)


@stream_bp.route('/dash/<string:torrent_title>/<path:filename>')
def dash_segment(torrent_title, filename):
    """
    Serves DASH segments or initialization segments as requested by the DASH player.
    """
    file_path = os.path.join(DASH_OUTPUT_DIR, torrent_title, filename)
    if os.path.exists(file_path):
        # Typically, DASH segments (fragmented MP4) have the MIME type video/iso.segment.
        return send_file(file_path, mimetype='video/iso.segment')
    else:
        return Response("Segment not found", status=404)
