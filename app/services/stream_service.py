import logging
import os
import subprocess

from flask import request, send_file

from app.services.config import MEDIA_EXTENSIONS, ffmpeg_path, DASH_OUTPUT_DIR


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


def process_mkv_to_dash(torrent_title, input_file_path, torrent_dir):
    """
    Uses FFmpeg to remux an MKV file into a DASH stream.
    - Copies the video stream (no re-encoding).
    - Transcodes/remuxes the first English audio stream to AAC for browser compatibility.
    - Generates DASH segments (10 seconds each) and an MPD manifest.
    The DASH output is written to a dedicated folder based on the torrent title.
    """
    # We'll use the torrent_title (which should correspond to the directory name of the torrent)
    output_dir = os.path.join(torrent_dir, DASH_OUTPUT_DIR)
    os.makedirs(output_dir, exist_ok=True)
    mpd_file = os.path.join(output_dir, "manifest.mpd")

    # If the DASH output already exists, we assume it’s ready.
    if os.path.exists(mpd_file):
        return mpd_file

    # Build the FFmpeg command.
    # Note: Adjust segment naming options (-init_seg_name and -media_seg_name) as needed.
    ffmpeg_command = [
        ffmpeg_path,
        "-y",  # Overwrite existing files if needed.
        "-i", input_file_path,  # Full path to the MKV file.
        "-c:v", "copy",  # Copy video stream.
        "-map", "0:v:0",  # Use first video stream.
        "-map", "0:a:m:language:eng",  # Select the English audio stream.
        "-c:a", "aac",  # Transcode audio to AAC.
        "-b:a", "192k",  # Audio bitrate.
        "-f", "dash",  # Output format: DASH.
        "-seg_duration", "10",  # 10-second segments.
        "-use_timeline", "1",  # Use timeline in MPD.
        "-use_template", "1",  # Use templates for segment naming.
        # Force FFmpeg to create segments with predictable names:
        "-init_seg_name", "init-$RepresentationID$.m4s",
        "-media_seg_name", "chunk-$RepresentationID$-$Number$.m4s",
        # Set a BaseURL so that the manifest uses URLs that point to your server's DASH endpoint:
        # "-base_url", f"/dash/{torrent_title}/{output_dir}/",
        os.path.join(output_dir, "manifest.mpd")
    ]

    try:
        subprocess.run(ffmpeg_command, check=True)
        logging.info("FFmpeg DASH process completed successfully")
    except subprocess.CalledProcessError as e:
        logging.error("FFmpeg DASH process failed: %s", e)
        return None

    return mpd_file
