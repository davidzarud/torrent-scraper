import threading

import requests
from app.services.config import QBITTORRENT_BASE_URL, QBITTORRENT_USERNAME, QBITTORRENT_PASSWORD
from app.services.jellyfin_service import notify_jellyfin
from app.services.utils import extract_season_episode, unescape_html
from flask import jsonify
from fuzzywuzzy import fuzz


def add_torrent_to_qbittorrent(magnet_link, context, title):
    from app.routes.torrents import qtorrent_session
    if not QBITTORRENT_BASE_URL or not QBITTORRENT_USERNAME or not QBITTORRENT_PASSWORD:
        print("qBittorrent credentials not set.")
        return False

    if not is_session_valid():
        if not login_to_qbittorrent():
            print("Failed to login to qBittorrent.")
            return False

    add_torrent_url = f"{QBITTORRENT_BASE_URL}/api/v2/torrents/add"
    title = unescape_html(title)
    data = {'urls': magnet_link, 'sequentialDownload': 'true', 'firstLastPiecePrio': 'true',
            'savepath': f'{context}/{title}'}
    try:
        response = qtorrent_session.post(add_torrent_url, data=data)
        response.raise_for_status()

        threading.Timer(5, notify_jellyfin).start()

        return True
    except requests.exceptions.RequestException as e:
        print(f"Error adding torrent: {e}")
        return False


def is_session_valid():
    from app.routes.torrents import qtorrent_session
    try:
        test_url = f"{QBITTORRENT_BASE_URL}/api/v2/auth/login"
        response = qtorrent_session.get(test_url)
        response.raise_for_status()
        if response.text != "Ok.":
            raise Exception("Session is not valid.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error adding torrent: {e}")
        return False


def login_to_qbittorrent():
    from app.routes.torrents import qtorrent_session
    login_url = f"{QBITTORRENT_BASE_URL}/api/v2/auth/login"
    data = {
        'username': QBITTORRENT_USERNAME,
        'password': QBITTORRENT_PASSWORD
    }
    try:
        response = qtorrent_session.post(login_url, data=data)
        response.raise_for_status()

        if response.text != "Ok.":
            print(f"Failed to log in: {response.text}")
            raise Exception("Failed to login to qBittorrent")

        # Print cookies to ensure session is set
        print(f"Login successful, session cookies: {qtorrent_session.cookies}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error logging in: {e}")
        return False


def get_torrent_by_title(title):
    from app.routes.torrents import qtorrent_session
    if not QBITTORRENT_BASE_URL or not QBITTORRENT_USERNAME or not QBITTORRENT_PASSWORD:
        print("qBittorrent credentials not set.")
        return jsonify({'error': 'qBittorrent credentials not set.'}), 400

    if not is_session_valid():
        if not login_to_qbittorrent():
            print("Failed to login to qBittorrent.")
            return jsonify({'error': 'Failed to login to qBittorrent.'}), 500
    print("title ", title)

    if not title:
        return jsonify({'error': 'No title provided.'}), 400

    torrents_info_url = f"{QBITTORRENT_BASE_URL}/api/v2/torrents/info"
    try:

        response = qtorrent_session.get(torrents_info_url)
        response.raise_for_status()
        torrents = response.json()
    except requests.RequestException as e:
        print(f"Error fetching torrents: {e}")
        return jsonify({'error': 'Error fetching torrents.'}), 500

    best_match = None
    highest_similarity = 0

    season, episode = extract_season_episode(title)

    for torrent in torrents:
        torrent_name = torrent['name']
        similarity = fuzz.ratio(torrent_name, title)

        if season and episode:
            season_episode_pattern = f"s{season}e{episode}"
            if season_episode_pattern.lower() not in torrent_name.lower():
                continue

        if similarity > highest_similarity:
            highest_similarity = similarity
            best_match = torrent

    if best_match:
        return best_match
    else:
        return jsonify({'error': 'No matching torrent found.'}), 404


def get_media_file_name(torrent_hash):
    from app.routes.torrents import qtorrent_session
    if not QBITTORRENT_BASE_URL or not QBITTORRENT_USERNAME or not QBITTORRENT_PASSWORD:
        print("qBittorrent credentials not set.")
        return jsonify({'error': 'qBittorrent credentials not set.'}), 400

    if not is_session_valid():
        if not login_to_qbittorrent():
            print("Failed to login to qBittorrent.")
            return jsonify({'error': 'Failed to login to qBittorrent.'}), 500

    if not torrent_hash:
        return jsonify({'error': 'No hash provided.'}), 400

    try:
        torrents_files_url = f"{QBITTORRENT_BASE_URL}/api/v2/torrents/files?hash={torrent_hash}"

        response = qtorrent_session.get(torrents_files_url)
        largest_file = max(response.json(), key=lambda file: file['size'])
        largest_file_name = largest_file['name']
        if '/' in largest_file_name:
            largest_file_name = largest_file_name.rsplit('/', 1)[-1]
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching torrents: {e}")
        return jsonify({'error': 'Error fetching torrent files.'}), 500
    return largest_file_name
