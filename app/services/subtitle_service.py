import logging
from json import load
from os import path
from time import time

import requests

from app.services.config import WIZDOM_DOMAIN, TMP_DIR, TMDB_KEY
from app.services.utils import normalize_str


def caching_json(filename, url):
    json_file = path.join(TMP_DIR, filename)
    if not path.exists(json_file) or path.getsize(json_file) <= 20 or (time() - path.getmtime(json_file) > 30 * 60):
        logging.debug(f"Fetching data from URL: {url}")
        response = requests.get(url)
        response.encoding = 'utf-8'
        with open(json_file, 'w', encoding='utf-8') as f:
            f.write(response.text)
    try:
        with open(json_file, 'r', encoding='utf-8') as json_data:
            return load(json_data)
    except UnicodeDecodeError as e:
        logging.error(f"UnicodeDecodeError: {e}")
    return {}


def convert_srt_to_vtt(srt_path, vtt_path):
    """Convert .srt subtitles to .vtt format and save to file."""
    try:
        with open(srt_path, "r", encoding="utf-8-sig") as infile:
            lines = infile.readlines()

        vtt_lines = ["WEBVTT\n\n"]
        for line in lines:
            vtt_lines.append(line.replace(",", ".") if "-->" in line else line)

        with open(vtt_path, "w", encoding="utf-8") as outfile:
            outfile.writelines(vtt_lines)
        return True
    except Exception as e:
        logging.error(f"Error converting SRT to VTT: {e}")
        return False


def search_by_imdb(imdb_id, season=0, episode=0, version=0):
    filename = f'wizdom.imdb.{imdb_id}.{season}.{episode}.json'
    url = (f"http://{WIZDOM_DOMAIN}/search?action=by_id&imdb={imdb_id}&season={season}&episode={episode}"
           f"&version={version}")
    return caching_json(filename, url)


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
        logging.error(f"Error extracting TMDB ID: {e}")
    return None
