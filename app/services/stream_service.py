import logging
import os
import subprocess

from flask import request, Response, send_file
from app.services.config import MEDIA_EXTENSIONS, ffmpeg_path


def find_media_files(directory_path, context, season_episode=None, follow_symlinks=False):
    """
    Recursively finds all media files in a directory (including subdirectories).
    - `context`: 'movies' or 'tv'.
    - `seasonEpisode`: String to search for in filenames (e.g., 'S01E01') for TV shows.
    - `follow_symlinks`: Set to `True` to follow symbolic links (default: `False` to avoid loops).
    Returns a list of dictionaries containing file paths and sizes in GB.
    """
    media_files = []

    if not os.path.isdir(directory_path):
        return media_files

    try:
        for entry in os.scandir(directory_path):
            if entry.is_file():
                # Check file extension
                _, ext = os.path.splitext(entry.name)
                if ext.lower() in MEDIA_EXTENSIONS:
                    if context == 'movies':
                        # Add all media files for movies
                        file_size_bytes = os.path.getsize(entry.path)
                        file_size_gb = file_size_bytes / (1024 ** 3)  # Convert bytes to GB
                        media_files.append({
                            'name': entry.name,
                            'path': entry.path,
                            'size': round(file_size_gb, 2)  # Round to 2 decimal places
                        })
                    elif context == 'tv' and season_episode:
                        # Check if the filename contains the seasonEpisode string (case-insensitive)
                        if season_episode.lower() in entry.name.lower():
                            file_size_bytes = os.path.getsize(entry.path)
                            file_size_gb = file_size_bytes / (1024 ** 3)  # Convert bytes to GB
                            media_files.append({
                                'name': entry.name,
                                'path': entry.path,
                                'size': round(file_size_gb, 2)  # Round to 2 decimal places
                            })
            elif entry.is_dir(follow_symlinks=follow_symlinks):
                # Recursively search subdirectories
                media_files.extend(find_media_files(entry.path, context, season_episode, follow_symlinks))
    except PermissionError:
        pass  # Skip directories we can't access

    return media_files


def stream_and_remux(torrent_title):
    media_file_path = request.args.get('file')
    if not os.path.exists(media_file_path):
        logging.error("Torrent file not found")
        return "File not found", 404

    logging.info("Torrent file found")
    # FFmpeg command to transcode and stream the video
    ffmpeg_command = [
        ffmpeg_path,
        '-i', media_file_path,
        '-c:v', 'copy',  # Copy the video codec (no re-encoding)
        '-map', '0:v:0',  # Select the first video stream
        '-map', '0:a:m:language:eng',  # Select the audio stream with language "eng"
        '-c:a', 'aac',  # Encode audio to AAC if necessary
        '-b:a', '192k',  # Set the audio bitrate
        '-preset', 'ultrafast',  # Use ultrafast preset for quicker encoding
        '-tune', 'fastdecode',  # Tune for faster decoding (useful for streaming)
        '-movflags', 'frag_keyframe+empty_moov',  # Optimize for streaming
        '-f', 'mp4',  # Output format
        'pipe:1'  # Streaming to stdout
    ]

    # Start FFmpeg process
    try:
        ffmpeg_process = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logging.info("ffmpeg process started")
    except Exception as e:
        logging.error(f"ffmpeg process failed: {e}")
        return "FFmpeg not found. Please ensure FFmpeg is installed and accessible.", 500

    # Stream the output of FFmpeg to the client
    return Response(ffmpeg_process.stdout, mimetype='video/mp4')


def stream_mp4(torrent_title):
    media_file_path = request.args.get('file')

    if not media_file_path or not os.path.exists(media_file_path):
        logging.error(f"File not found: {media_file_path}")
        return "File not found", 404

    logging.info(f"Serving MP4 file: {media_file_path}")

    return send_file(
        media_file_path,
        mimetype="video/mp4",
        as_attachment=False
    )