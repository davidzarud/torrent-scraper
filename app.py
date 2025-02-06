import logging
import platform
import re
import shutil
import threading
import zipfile
import subprocess
from json import load
from os import makedirs, path
from time import time

from flask import Flask, send_from_directory, request, jsonify, Response
from flask_cors import CORS
from unicodedata import normalize, combining

from config import *
from services.html_service import search_torrents, fetch_magnet_link
from services.jellyfin_service import notify_jellyfin
from services.qbittorrent_service import add_torrent_to_qbittorrent
from services.tmdb_service import *
from services.utils import unescape_html

app = Flask(__name__, static_folder="static", static_url_path="/static")
CORS(app)
app.secret_key = os.urandom(24)
is_windows = platform.system() == 'Windows'
ffmpeg_path = os.getenv('FFMPEG_PATH', 'ffmpeg')  # Default to 'ffmpeg' if not set

session = requests.Session()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


@app.route('/api/movies')
def movies_api():
    page = request.args.get('page', default=1, type=int)
    sort = request.args.get('sort', default='popular', type=str)

    if sort == 'popular':
        movies_result, total_pages = get_popular_bluray_movies(page)
    elif sort == 'trending':
        movies_result, total_pages = get_trending_movies(page)
    elif sort == 'watchlist':
        movies_result, total_pages = get_movie_watchlist(page)
    else:
        movies_result, total_pages = get_top_rated_movies(page)

    # Return the movies result and optionally the total pages.
    return jsonify({
        'movies': movies_result,
        'page': page,
        'total_pages': total_pages
    })


@app.route('/api/movie/<int:movie_id>')
def movie_detail(movie_id):
    url = f"{TMDB_BASE_URL}/movie/{movie_id}"
    params = {'api_key': TMDB_KEY}
    response = requests.get(url, params=params)
    movie_data = response.json()

    genres = [genre['name'] for genre in movie_data.get('genres', [])]
    genre_string = ', '.join(genres)

    credits_url = f"{TMDB_BASE_URL}/movie/{movie_id}/credits"
    credits_response = requests.get(credits_url, params=params)
    credits_data = credits_response.json()
    cast = [member['name'] for member in credits_data.get('cast', [])[:5]]
    cast_string = ', '.join(cast)

    vote_average = movie_data.get('vote_average', 0)
    user_score_percentage = round(vote_average * 10)

    movie = {
        'title': movie_data.get('title'),
        'release_date': movie_data.get('release_date'),
        'poster_path': movie_data.get('poster_path'),
        'overview': movie_data.get('overview'),
        'genre': genre_string,
        'cast': cast_string,
        'user_score_percentage': user_score_percentage
    }

    torrents = search_torrents(f"{movie_data.get('title')} {movie_data.get('release_date')[:4]}")
    return jsonify({
        'title': movie,
        'torrents': torrents
    })


@app.route('/api/movies/search')
def search_movies():
    query = request.args.get('query', '')
    page = request.args.get('page', 1)
    response = []
    if query:
        response = search_movies_by_name(query, page)
    return jsonify({
        'page': response.get('page'),
        'total_pages': response.get('total_pages'),
        'movies': response.get('results')
    })


@app.route('/api/tv')
def home_tv():
    page = request.args.get('page', default=1, type=int)
    sort = request.args.get('sort', default='popular', type=str)

    if sort == 'top-rated':
        shows, total_pages = get_top_rated_shows(page)
    elif sort == 'trending':
        shows, total_pages = get_trending_shows(page)
    elif sort == 'watchlist':
        shows, total_pages = get_tv_watchlist(page)
    else:
        shows, total_pages = get_popular_running_shows(page)
    return jsonify({
        'movies': shows,
        'page': page,
        'total_pages': total_pages
    })


@app.route('/api/tv/<int:show_id>')
def show_detail(show_id):
    # Fetch show details
    url = f"{TMDB_BASE_URL}/tv/{show_id}?append_to_response=credits"
    params = {'api_key': TMDB_KEY}
    response = requests.get(url, params=params)
    show_data = response.json()

    # Fetch seasons and episodes
    seasons = show_data.get('seasons', [])
    seasons = [season for season in seasons if season.get('season_number') != 0]  # Filter out season 0

    vote_average = show_data.get('vote_average', 0)
    user_score_percentage = round(vote_average * 10)

    for season in seasons:
        season_number = season.get('season_number')
        episodes_url = f"{TMDB_BASE_URL}/tv/{show_id}/season/{season_number}"
        episodes_response = requests.get(episodes_url, params=params)
        episodes_data = episodes_response.json()
        season['episodes'] = [episode['episode_number'] for episode in episodes_data.get('episodes', [])]

    show = {
        'name': show_data.get('name'),
        'release_date': show_data.get('first_air_date'),
        'poster_path': show_data.get('poster_path'),
        'overview': show_data.get('overview'),
        'genre': ', '.join([genre['name'] for genre in show_data.get('genres', [])]),
        'cast': ', '.join([member['name'] for member in show_data.get('credits', {}).get('cast', [])[:5]]),
        'user_score_percentage': user_score_percentage
    }

    return jsonify({
        'title': show,
        'seasons': seasons
    })


@app.route('/api/tv/search')
def search_tv_shows():
    query = request.args.get('query', '')
    page = request.args.get('page', 1)
    response = []
    if query:
        response = search_tv_shows_by_name(query, page)
    return jsonify({
        'page': response.get('page'),
        'total_pages': response.get('total_pages'),
        'movies': response.get('results')
    })


@app.route('/api/get_magnet_link', methods=['POST'])
def get_magnet_link():
    data = request.get_json()
    torrent_url = data.get('torrent_url')
    context = data.get('context')
    title = re.sub(r'[<>:"/\\|?*]', '', data.get('title'))
    magnet_link = fetch_magnet_link(torrent_url)
    if magnet_link:
        success = add_torrent_to_qbittorrent(magnet_link, context, title)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to add torrent to qBittorrent'})
    else:
        return jsonify({'success': False, 'error': 'Failed to fetch magnet link'})


@app.route('/tmdb/watchlist/<media_type>/<action>/<title_id>', methods=['POST'])
def toggle_watchlist(media_type, action, title_id):
    success = toggle_item_watchlist(media_type, action, title_id)
    if success:
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Failed to toggle watchlist item'})


@app.route('/api/search_torrents')
def search_torrents_route():
    query = request.args.get('query')
    if query:
        torrents = search_torrents(query)
        return jsonify({'torrents': torrents})
    return jsonify({'torrents': []})


@app.route('/api/search_sub', methods=['POST'])
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


@app.route('/api/download/<int:sub_id>/<string:name>', methods=['POST'])
def download_subtitle(sub_id, name):
    try:
        url = f"http://{WIZDOM_DOMAIN}/files/sub/{sub_id}"
        response = requests.get(url, verify=False)
        response.raise_for_status()

        data = request.get_json()
        movie_title, context = data.get('movie_title'), data.get('context')

        if context == 'tv':
            tv_show_pattern = re.search(r's\d{2}e\d{2}', name, re.IGNORECASE).group()
            video_file = find_media_file(DOWNLOADS_BASE_PATH, movie_title, context, tv_show_pattern)
        else:
            video_file = find_media_file(DOWNLOADS_BASE_PATH, movie_title, context, is_movie=True)

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

        threading.Timer(10, lambda: notify_jellyfin()).start()

        return jsonify({"success": True, "message": f"Subtitle '{name}' downloaded and extracted successfully."})
    except (requests.RequestException, zipfile.BadZipFile) as e:
        app.logger.error(f"Error during subtitle processing: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route('/api/title-exists')
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


@app.route('/stream/<string:torrent_title>')
def stream(torrent_title):
    if is_windows:
        mkv_file_path = f'\\\\192.168.1.194\\data\\downloads\\test.mkv'
        # mkv_file_path = f'\\\\192.168.1.194\\data\\downloads\\{torrent_title}'
    else:
        mkv_file_path = f'{DOWNLOADS_BASE_PATH}/test.mkv'

    # Check if the file exists
    if not os.path.exists(mkv_file_path):
        logging.error("Torrent file not found")
        return "File not found", 404

    logging.info("Torrent file found")
    # FFmpeg command to transcode and stream the video
    ffmpeg_command = [
        ffmpeg_path,  # Use the FFmpeg path from the environment variable
        '-i', mkv_file_path,
        '-f', 'mp4',
        '-movflags', 'frag_keyframe+empty_moov',
        '-'
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


def find_media_files(directory_path, context, seasonEpisode=None, follow_symlinks=False):
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
                    elif context == 'tv' and seasonEpisode:
                        # Check if the filename contains the seasonEpisode string (case-insensitive)
                        if seasonEpisode.lower() in entry.name.lower():
                            file_size_bytes = os.path.getsize(entry.path)
                            file_size_gb = file_size_bytes / (1024 ** 3)  # Convert bytes to GB
                            media_files.append({
                                'name': entry.name,
                                'path': entry.path,
                                'size': round(file_size_gb, 2)  # Round to 2 decimal places
                            })
            elif entry.is_dir(follow_symlinks=follow_symlinks):
                # Recursively search subdirectories
                media_files.extend(find_media_files(entry.path, context, seasonEpisode, follow_symlinks))
    except PermissionError:
        pass  # Skip directories we can't access

    return media_files


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
    title = re.sub(r'[?*/\\":<>|]', '', title)
    title = unescape_html(title)
    base_path = os.path.join(directory, context.lower())
    target_dir = os.path.join(str(base_path), title)
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


def search_tmdb(media_type, query, year=None):
    normalized_query = normalize_str(query.replace('&amp;', '&'))
    filename = f'wizdom.search.tmdb.{media_type}.{normalized_query}.{year}.json'
    url = (f"https://api.tmdb.org/3/search/{media_type}?api_key={TMDB_KEY}&query={normalized_query}"
           f"&year={year or ''}").rstrip('&year=')

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
    url = (f"http://{WIZDOM_DOMAIN}/search?action=by_id&imdb={imdb_id}&season={season}&episode={episode}"
           f"&version={version}")
    return caching_json(filename, url)


# Serve the frontend
@app.route("/")
def serve_frontend():
    return send_from_directory("static", "index.html")


# Catch-all route for Vue/React-style SPA routing
@app.route("/<path:path>")
def catch_all(path):
    return send_from_directory("static", "index.html")


if __name__ == '__main__':
    makedirs(TMP_DIR, exist_ok=True)
    makedirs(SUBS_DIR, exist_ok=True)
    app.run(host="0.0.0.0", port=5000, debug=True)
