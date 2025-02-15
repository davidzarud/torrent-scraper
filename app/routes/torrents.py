import re

import requests
from app.services.html_service import fetch_magnet_link, search_torrents
from app.services.qbittorrent_service import add_torrent_to_qbittorrent
from flask import Blueprint, jsonify, request

torrents_bp = Blueprint("torrents", __name__, url_prefix="")

qtorrent_session = requests.session()


@torrents_bp.route("/api/get_magnet_link", methods=["POST"])
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


@torrents_bp.route("/api/search_torrents")
def search_torrents_route():
    query = request.args.get('query')
    if query:
        torrents = search_torrents(query)
        return jsonify({'torrents': torrents})
    return jsonify({'torrents': []})
