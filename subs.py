import os
import re
import shutil
from json import loads, load
from os import path
from time import time

import requests
from flask import Flask, request, jsonify
from fuzzywuzzy import fuzz
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

        # Download the subtitle file
        response = requests.get(url, verify=False)
        response.raise_for_status()  # Raise an error for HTTP error responses

        data = request.get_json()
        movie_title = data.get('movie_title')
        app.logger.info(f"movie title: {movie_title}")

        closest_file_path = find_closest_file(SUB_SEARCH_DIR, movie_title)
        if not closest_file_path:
            app.logger.error("No matching media file found.")
            return jsonify({"success": False, "message": "No matching media file found."}), 404

        app.logger.info(f"Closest matching file found: {closest_file_path}")

        content_path = os.path.dirname(closest_file_path)
        media_file_name = re.sub(r'\.[^.]+$', '', os.path.basename(closest_file_path))

        app.logger.info(f"Content path: {content_path}")
        app.logger.info(f"Media file name: {media_file_name}")

        # Save the file locally (optional, if you want to save it before sending it to the user)
        filename = f"{media_file_name}.srt"  # Change the extension based on your file type
        filepath = path.join(SUBS_DIR, filename)
        with open(filepath, 'wb') as file:
            file.write(response.content)

        # Move the file to the content_path directory
        destination_filepath = path.join(content_path, filename)
        app.logger.info(f"Destination path: {destination_filepath}")
        shutil.move(filepath, destination_filepath)

        return jsonify({"success": True, "message": f"Subtitle '{name}' downloaded successfully."})

    except requests.RequestException as e:
        app.logger.error(f"Error fetching subtitle file: {e}")
        return jsonify({"success": False, "message": "Failed to download subtitle."}), 500


def find_closest_file(directory, movie_title):
    closest_match = None
    highest_ratio = 0

    # Check if the movie title contains a season/episode pattern
    tv_show_pattern = re.search(r's\d{2}e\d{2}', movie_title, re.IGNORECASE)

    # Walk through the directory tree
    for root, dirs, files in os.walk(directory):
        for file_name in files:
            # Normalize file names for comparison (remove extensions, convert to lowercase)
            normalized_file_name = re.sub(r'\.[^.]+$', '', file_name).lower()
            normalized_title = movie_title.lower()

            # If it's a TV show, try to match the sXXeYY pattern
            if tv_show_pattern:
                episode_pattern = tv_show_pattern.group()
                if episode_pattern.lower() in normalized_file_name:
                    ratio = fuzz.ratio(normalized_title, normalized_file_name)
                else:
                    continue  # Skip this file if it doesn't contain the episode pattern
            else:
                # Use fuzzywuzzy to find the closest match for movies
                ratio = fuzz.ratio(normalized_title, normalized_file_name)

            if ratio > highest_ratio:
                highest_ratio = ratio
                closest_match = os.path.join(root, file_name)

    return closest_match
