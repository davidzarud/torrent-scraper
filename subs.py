import os
import re
import shutil
import threading
import zipfile
from json import loads, load
from os import path
from time import time

import requests
from flask import Flask, request, jsonify
from unicodedata import normalize, combining

app = Flask(__name__)

# Global variable
global_imdb_id = None

# Configuration
TMP_DIR = 'tmp'
SUBS_DIR = 'subs'
MY_DOMAIN = 'wizdom.xyz/api'

TMDB_KEY = os.getenv('TMDB_KEY')
SUB_SEARCH_DIR = os.getenv('SUB_SEARCH_DIR')


@app.route('/search_sub', methods=['POST'])
def search():
    global global_imdb_id
    title = request.form.get('title')
    media_type = request.form.get('type')

    print('title: ', title)
    print('mediatype: ', media_type)

    year = None
    if request.form.get('year'):
        year = request.form.get('year')[:4]
    season, episode = 0, 0

    # Extract season and episode from title if present
    match = re.search(r's(\d+)(e(\d+))?', title, re.IGNORECASE)
    if match:
        season = int(match.group(1))
        if match.group(3):
            episode = int(match.group(3))
        title = re.sub(r's\d+e?\d*', '', title, flags=re.IGNORECASE).strip()

    global_imdb_id = search_tmdb(media_type, title, year)
    print("global imdb id = ", global_imdb_id)

    subtitles = []
    if global_imdb_id:
        results = search_by_imdb(global_imdb_id, season, episode)
        print(f"search() - from imdb: {results}")
        subtitles = [{'id': result['id'], 'versioname': result['versioname']} for result in results if
                     'versioname' in result]
    return jsonify({'subtitles': subtitles})


def search_tmdb(media_type, query, year=None):
    # Normalize and prepare the query
    query = query.replace('&amp;', '&')
    normalized_query = normalize_str(query)

    # Build the filename and URL
    filename = f'wizdom.search.tmdb.{media_type}.{normalized_query}.{year}.json'
    url = f"https://api.tmdb.org/3/search/{media_type}?api_key={TMDB_KEY}&query={normalized_query}&year={year}" if year else \
        f"https://api.tmdb.org/3/search/{media_type}?api_key={TMDB_KEY}&query={normalized_query}"

    # Log URL being requested
    app.logger.debug(f"TMDB Search URL: {url}")

    # Fetch and cache JSON
    json = caching_json(filename, url)

    # Log raw response
    app.logger.debug(f"TMDB Response JSON: {json}")

    try:
        results = json.get("results", [])
        if results:
            if media_type == 'tv':
                # Sort results by popularity and get the most popular one
                filtered_results = [result for result in results if result.get('name', '').lower() == query.lower()]
            else:
                filtered_results = [result for result in results if result.get('title', '').lower() == query.lower()]
            if filtered_results:
                most_popular_result = sorted(filtered_results, key=lambda x: x.get('popularity', 0), reverse=True)[0]
            else:
                most_popular_result = None  # Or handle the case where no exact match is found
            tmdb_id = int(most_popular_result["id"])
            url = f"https://api.tmdb.org/3/{media_type}/{tmdb_id}/external_ids?api_key={TMDB_KEY}"
            response = requests.get(url)
            json = loads(response.text)
            app.logger.debug(f"TMDB {media_type.capitalize()} External IDs Response: {json}")
            return json.get("imdb_id")
    except (IndexError, KeyError) as e:
        app.logger.error(f"Error extracting TMDB ID: {e}")
        return None


def search_by_imdb(imdb_id, season=0, episode=0, version=0):
    filename = f'wizdom.imdb.{imdb_id}.{season}.{episode}.json'
    url = f"http://{MY_DOMAIN}/search?action=by_id&imdb={imdb_id}&season={season}&episode={episode}&version={version}"
    app.logger.debug(f"Searching by IMDb ID with URL: {url}")
    json = caching_json(filename, url)
    return json


def normalize_str(s):
    print(f"Normalizing string: {s}")
    normalized = normalize('NFKD', s)
    normalized = ''.join(c for c in normalized if not combining(c))
    print(f"Normalized string: {normalized}")
    return normalized


def caching_json(filename, url):
    json_file = path.join(TMP_DIR, filename)
    if not path.exists(json_file) or not path.getsize(json_file) > 20 or (time() - path.getmtime(json_file) > 30 * 60):
        app.logger.debug(f"Fetching data from URL: {url}")
        response = requests.get(url)
        response.encoding = 'utf-8'
        with open(json_file, 'w', encoding='utf-8') as f:
            f.write(response.text)
    if path.exists(json_file) and path.getsize(json_file) > 20:
        try:
            with open(json_file, 'r', encoding='utf-8') as json_data:
                app.logger.debug(f"Reading data from file: {json_file}")
                return load(json_data)
        except UnicodeDecodeError as e:
            app.logger.error(f"UnicodeDecodeError: {e}")
    return {}


@app.route('/download/<int:sub_id>/<string:name>', methods=['POST'])
def download_subtitle(sub_id, name):
    try:
        # Construct the URL for fetching the subtitle file
        url = f"http://{MY_DOMAIN}/files/sub/{sub_id}"
        app.logger.info(f"Fetching subtitle from URL: {url}")
        app.logger.info(f"Subtitle name: {name}, Subtitle id: {sub_id}")

        # Download the subtitle .zip file
        response = requests.get(url, verify=False)
        response.raise_for_status()  # Raise an error for HTTP error responses

        data = request.get_json()
        movie_title = data.get('movie_title')
        context = data.get('context')
        if context == 'tv':
            tv_show_pattern = re.search(r's\d{2}e\d{2}', name, re.IGNORECASE).group()
            video_file = find_episode(SUB_SEARCH_DIR, movie_title, context, tv_show_pattern)
        else:
            video_file = find_movie(SUB_SEARCH_DIR, movie_title, context)

        app.logger.info(f"Movie title: {movie_title}")

        # closest_file_path = find_episode(SUB_SEARCH_DIR, movie_title, context, tv_show_pattern)
        if not video_file:
            app.logger.error("No matching media file found.")
            return jsonify({"success": False, "message": "No matching media file found."}), 404

        app.logger.info(f"Closest matching file found: {video_file}")

        content_path = os.path.dirname(video_file)
        media_file_name = re.sub(r'\.[^.]+$', '', os.path.basename(video_file))

        app.logger.info(f"Content path: {content_path}")
        app.logger.info(f"Media file name: {media_file_name}")

        # Save the .zip file locally
        zip_filename = f"{media_file_name}.zip"
        zip_filepath = os.path.join(SUBS_DIR, zip_filename)
        with open(zip_filepath, 'wb') as file:
            file.write(response.content)

        # Extract the .srt file from the .zip archive
        with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
            # Look for the .srt file within the zip archive
            srt_file = next((f for f in zip_ref.namelist() if f.endswith('.srt')), None)
            if srt_file:
                zip_ref.extract(srt_file, SUBS_DIR)
            else:
                app.logger.error("No .srt file found in the zip archive.")
                return jsonify({"success": False, "message": "No .srt file found in the zip archive."}), 400

        # Determine the final file path for the .srt file
        extracted_srt_path = os.path.join(SUBS_DIR, srt_file)
        final_srt_path = os.path.join(content_path, f"{media_file_name}.heb.srt")

        # Move the .srt file to the content_path directory
        shutil.move(extracted_srt_path, final_srt_path)

        # Cleanup: remove the downloaded .zip file
        os.remove(zip_filepath)

        from app import notify_jellyfin
        threading.Timer(10, notify_jellyfin).start()

        return jsonify({"success": True, "message": f"Subtitle '{name}' downloaded and extracted successfully."})

    except requests.RequestException as e:
        app.logger.error(f"Error fetching subtitle file: {e}")
        return jsonify({"success": False, "message": "Failed to download subtitle."}), 500

    except zipfile.BadZipFile as e:
        app.logger.error(f"Error extracting subtitle file: {e}")
        return jsonify({"success": False, "message": "Failed to extract subtitle."}), 500


def find_episode(directory, title, context, tv_show_pattern):
    # Define the base path and target directory
    base_path = os.path.join(directory, context.lower())
    target_dir = os.path.join(base_path, title)

    # Check if the target directory exists
    if not os.path.exists(target_dir):
        print(f"Directory '{target_dir}' does not exist.")
        return None

    # Normalize the tv_show_pattern to lowercase
    normalized_pattern = tv_show_pattern.lower()

    # Walk through the target directory recursively
    for root, dirs, files in os.walk(target_dir):
        for file_name in files:
            # Check if the file has a .mkv or .mp4 extension
            if file_name.lower().endswith(('.mkv', '.mp4')):
                # Normalize the file name to lowercase
                normalized_file_name = file_name.lower()

                # Check if the normalized pattern is in the normalized file name
                if normalized_pattern in normalized_file_name:
                    # Return the full path of the matching file
                    return os.path.join(root, file_name)

    # If no matching file is found, return None
    print(f"No file with pattern '{tv_show_pattern}' found in '{target_dir}'.")
    return None


def find_movie(directory, title, context):
    # Define the base path and target directory
    base_path = os.path.join(directory, context.lower())
    target_dir = os.path.join(base_path, title)

    # Check if the target directory exists
    if not os.path.exists(target_dir):
        print(f"Directory '{target_dir}' does not exist.")
        return None

    movie_file = None
    largest_size = 0

    # Walk through the target directory recursively
    for root, dirs, files in os.walk(target_dir):
        for file_name in files:
            # Check if the file has a .mkv or .mp4 extension
            if file_name.lower().endswith(('.mkv', '.mp4')):
                # Get the full path of the file
                file_path = os.path.join(root, file_name)

                # Get the size of the file
                file_size = os.path.getsize(file_path)

                # Check if this is the largest file found so far
                if file_size > largest_size:
                    largest_size = file_size
                    movie_file = file_path

    if movie_file:
        print(f"Largest file found: {movie_file} ({largest_size} bytes)")
    else:
        print("No .mkv or .mp4 files found.")

    return movie_file
