import logging
import os
import re
import shutil
import threading
import zipfile

import requests
from flask import Blueprint, jsonify, request

from app.services.config import WIZDOM_DOMAIN, SUBS_DIR, DOWNLOADS_BASE_PATH
from app.services.jellyfin_service import notify_jellyfin
from app.services.subtitle_service import search_by_imdb, convert_srt_to_vtt
from app.services.tmdb_service import search_tmdb
from app.services.utils import extract_media_info, find_media_file

subtitles_bp = Blueprint("subtitles", __name__, url_prefix="")


@subtitles_bp.route('/api/search_sub', methods=['POST'])
def search():
    title = request.json['title']
    media_type = request.json['type']
    year = request.json.get('year', '')
    title, season, episode = extract_media_info(title)

    global_imdb_id = search_tmdb(media_type, title, year)
    if not global_imdb_id:
        return jsonify({'subtitles': []})

    results = search_by_imdb(global_imdb_id, season, episode)
    subtitles = [{'id': result['id'], 'versioname': result['versioname']} for result in results if
                 'versioname' in result]
    return jsonify({'subtitles': subtitles})


@subtitles_bp.route('/api/download/<int:sub_id>/<string:name>', methods=['POST'])
def download_subtitle(sub_id, name):
    try:
        url = f"http://{WIZDOM_DOMAIN}/files/sub/{sub_id}"
        response = requests.get(url, verify=False)
        response.raise_for_status()

        data = request.get_json()
        movie_title, context = data.get('movie_title'), data.get('context')

        # Determine correct video file location
        if context == 'tv':
            tv_show_pattern = re.search(r's\d{2}e\d{2}', name, re.IGNORECASE).group()
            video_file = find_media_file(DOWNLOADS_BASE_PATH, movie_title, context, tv_show_pattern)
        else:
            video_file = find_media_file(DOWNLOADS_BASE_PATH, movie_title, context, is_movie=True)

        if not video_file:
            return jsonify({"success": False, "message": "No matching media file found."}), 404

        media_file_name = re.sub(r'\.[^.]+$', '', os.path.basename(video_file))
        zip_filepath = os.path.join(SUBS_DIR, f"{media_file_name}.zip")

        # Save the downloaded ZIP file
        with open(zip_filepath, 'wb') as file:
            file.write(response.content)

        # Extract SRT file from ZIP
        with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
            srt_file = next((f for f in zip_ref.namelist() if f.endswith('.srt')), None)
            if not srt_file:
                return jsonify({"success": False, "message": "No .srt file found in the zip archive."}), 400
            zip_ref.extract(srt_file, SUBS_DIR)

        # Define final subtitle paths
        final_srt_path = os.path.join(os.path.dirname(video_file), f"{media_file_name}.heb.srt")
        final_vtt_path = os.path.join(os.path.dirname(video_file), f"{media_file_name}.heb.vtt")

        # Move the extracted SRT to its final location
        shutil.move(os.path.join(SUBS_DIR, srt_file), final_srt_path)

        # Convert and save as VTT
        if not convert_srt_to_vtt(final_srt_path, final_vtt_path):
            return jsonify({"success": False, "message": "Subtitle saved but failed to convert to VTT."}), 500

        # Cleanup ZIP file
        os.remove(zip_filepath)

        # Notify Jellyfin (asynchronously)
        threading.Timer(10, lambda: notify_jellyfin()).start()

        return jsonify({
            "success": True,
            "message": f"Subtitle '{name}' downloaded, extracted, and converted to VTT successfully.",
            "srt_path": final_srt_path,
            "vtt_path": final_vtt_path
        })
    except (requests.RequestException, zipfile.BadZipFile) as e:
        logging.error(f"Error during subtitle processing: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@subtitles_bp.route('/subtitles/list')
def list_subtitles():
    vtt_files = []
    media_dir = os.path.dirname(request.args.get('file').lower())
    for file in os.scandir(media_dir):
        _, ext = os.path.splitext(file.name)
        if ext == '.vtt':
            vtt_files.append({'name': file.name, 'path': file.path})

    return jsonify(vtt_files)
