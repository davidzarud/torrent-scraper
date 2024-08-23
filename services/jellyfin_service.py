import logging

from config import JELLYFIN_BASE_URL, JELLYFIN_API_KEY
from flask import jsonify
import requests


def notify_jellyfin():
    if not JELLYFIN_BASE_URL or not JELLYFIN_API_KEY:
        print("Jellyfin credentials not set.")
        return jsonify({'error': 'Jellyfin credentials not set.'}), 400

    scan_library_url = (f'{JELLYFIN_BASE_URL}/ScheduledTasks/Running/7738148ffcd07979c7ceb148e06b3aed'
                        f'?api_key={JELLYFIN_API_KEY}')
    try:
        response = requests.post(url=scan_library_url)
        response.raise_for_status()
    except requests.RequestException as e:
        logging.error(f'Failed to notify Jellyfin: {e}')
        return jsonify({"success": False, "message": "Failed to scan library."}), 500
