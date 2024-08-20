import os
import re
import shutil
import threading
import zipfile
from json import load
from os import path
from time import time

import requests
from flask import Flask, request, jsonify
from unicodedata import normalize, combining

from config import TMP_DIR, TMDB_KEY, WIZDOM_DOMAIN, SUB_SEARCH_DIR, SUBS_DIR

app = Flask(__name__)


# Helper Functions
def normalize_str(s):
    normalized = normalize('NFKD', s)
    return ''.join(c for c in normalized if not combining(c))


def caching_json(filename, url):
    json_file = path.join(TMP_DIR, filename)
    if not path.exists(json_file) or path.getsize(json_file) <= 20 or (time() - path.getmtime(json_file) > 30 * 60):
        app.logger.debug(f"Fetching data from URL: {url}")
        response = requests.get(url)
        response.encoding = 'utf-8'
        with open(json_file, 'w', encoding='utf-8') as f:
            f.write(response.text)
    try:
        with open(json_file, 'r', encoding='utf-8') as json_data:
            return load(json_data)
    except UnicodeDecodeError as e:
        app.logger.error(f"UnicodeDecodeError: {e}")
    return {}


def extract_media_info(title):
    season, episode = 0, 0
    match = re.search(r's(\d+)(e(\d+))?', title, re.IGNORECASE)
    if match:
        season = int(match.group(1))
        if match.group(3):
            episode = int(match.group(3))
        title = re.sub(r's\d+e?\d*', '', title, flags=re.IGNORECASE).strip()
    return title, season, episode


def find_media_file(directory, title, context, pattern=None, is_movie=False):
    base_path = os.path.join(directory, context.lower())
    target_dir = os.path.join(base_path, title)
    if not os.path.exists(target_dir):
        app.logger.error(f"Directory '{target_dir}' does not exist.")
        return None

    best_file = None
    largest_size = 0 if is_movie else None
    for root, _, files in os.walk(target_dir):
        for file_name in files:
            if file_name.lower().endswith(('.mkv', '.mp4')):
                if is_movie:
                    file_path = os.path.join(root, file_name)
                    file_size = os.path.getsize(file_path)
                    if file_size > largest_size:
                        largest_size = file_size
                        best_file = file_path
                elif pattern and pattern.lower() in file_name.lower():
                    return os.path.join(root, file_name)

    return best_file


# Routes
@app.route('/search_sub', methods=['POST'])
def search():
    title = request.form.get('title')
    media_type = request.form.get('type')
    year = request.form.get('year', '')[:4]
    title, season, episode = extract_media_info(title)

    global_imdb_id = search_tmdb(media_type, title, year)
    if not global_imdb_id:
        return jsonify({'subtitles': []})

    results = search_by_imdb(global_imdb_id, season, episode)
    subtitles = [{'id': result['id'], 'versioname': result['versioname']} for result in results if
                 'versioname' in result]
    return jsonify({'subtitles': subtitles})


def search_tmdb(media_type, query, year=None):
    normalized_query = normalize_str(query.replace('&amp;', '&'))
    filename = f'wizdom.search.tmdb.{media_type}.{normalized_query}.{year}.json'
    url = f"https://api.tmdb.org/3/search/{media_type}?api_key={TMDB_KEY}&query={normalized_query}&year={year or ''}".rstrip(
        '&year=')

    json_data = caching_json(filename, url)
    try:
        results = json_data.get("results", [])
        if results:
            filtered_results = [result for result in results if
                                result.get('name' if media_type == 'tv' else 'title', '').lower() == query.lower()]
            if filtered_results:
                most_popular = sorted(filtered_results, key=lambda x: x.get('popularity', 0), reverse=True)[0]
                tmdb_id = most_popular["id"]
                external_url = f"https://api.tmdb.org/3/{media_type}/{tmdb_id}/external_ids?api_key={TMDB_KEY}"
                external_data = requests.get(external_url).json()
                return external_data.get("imdb_id")
    except (IndexError, KeyError) as e:
        app.logger.error(f"Error extracting TMDB ID: {e}")
    return None


def search_by_imdb(imdb_id, season=0, episode=0, version=0):
    filename = f'wizdom.imdb.{imdb_id}.{season}.{episode}.json'
    url = f"http://{WIZDOM_DOMAIN}/search?action=by_id&imdb={imdb_id}&season={season}&episode={episode}&version={version}"
    return caching_json(filename, url)


@app.route('/download/<int:sub_id>/<string:name>', methods=['POST'])
def download_subtitle(sub_id, name):
    try:
        url = f"http://{WIZDOM_DOMAIN}/files/sub/{sub_id}"
        response = requests.get(url, verify=False)
        response.raise_for_status()

        data = request.get_json()
        movie_title, context = data.get('movie_title'), data.get('context')

        if context == 'tv':
            tv_show_pattern = re.search(r's\d{2}e\d{2}', name, re.IGNORECASE).group()
            video_file = find_media_file(SUB_SEARCH_DIR, movie_title, context, tv_show_pattern)
        else:
            video_file = find_media_file(SUB_SEARCH_DIR, movie_title, context, is_movie=True)

        if not video_file:
            return jsonify({"success": False, "message": "No matching media file found."}), 404

        media_file_name = re.sub(r'\.[^.]+$', '', os.path.basename(video_file))
        zip_filepath = os.path.join(SUBS_DIR, f"{media_file_name}.zip")
        with open(zip_filepath, 'wb') as file:
            file.write(response.content)

        with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
            srt_file = next((f for f in zip_ref.namelist() if f.endswith('.srt')), None)
            if not srt_file:
                return jsonify({"success": False, "message": "No .srt file found in the zip archive."}), 400
            zip_ref.extract(srt_file, SUBS_DIR)

        final_srt_path = os.path.join(os.path.dirname(video_file), f"{media_file_name}.heb.srt")
        shutil.move(os.path.join(SUBS_DIR, srt_file), final_srt_path)
        os.remove(zip_filepath)

        from app import notify_jellyfin
        threading.Timer(10, lambda: notify_jellyfin()).start()

        return jsonify({"success": True, "message": f"Subtitle '{name}' downloaded and extracted successfully."})
    except (requests.RequestException, zipfile.BadZipFile) as e:
        app.logger.error(f"Error during subtitle processing: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


if __name__ == '__main__':
    app.run()
