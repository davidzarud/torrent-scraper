import logging
import os
import re
import subprocess
import threading
from json import load
from os import path
from time import time

import pysubs2
import requests

import app.services.config as config
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


def get_first_subtitle_track(mkv_file):
    """Finds the first subtitle track ID in an MKV file."""
    result = subprocess.run(["mkvmerge", "-i", mkv_file], capture_output=True, text=True)

    for line in result.stdout.splitlines():
        match = re.search(r"Track ID (\d+): subtitles \(SubRip/SRT\)", line, re.IGNORECASE)
        if match:
            return match.group(1)  # Return the first subtitle track ID

    return None  # No subtitles found


def extract_first_subtitle(mkv_file, output_srt):
    """Extracts the first detected subtitle track."""
    track_id = get_first_subtitle_track(mkv_file)
    if track_id is None:
        print("No subtitle track found!")
        return False

    command = ["mkvextract", "tracks", mkv_file, f"{track_id}:{output_srt}"]
    try:
        subprocess.run(command, check=True)
        print(f"Extracted first subtitle track (ID {track_id}) to {output_srt}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error extracting subtitles: {e}")
        return False


def sync_with_ffsubsync(synchronized_sub, unsynchronized_sub, video_file):
    extracted_sub_exists = True
    extracted_subtitle_file = os.path.splitext(video_file)[0] + ".extracted.srt"
    if not os.path.exists(extracted_subtitle_file):
        extracted_sub_exists = extract_first_subtitle(video_file, extracted_subtitle_file)

    # Build the command array
    command = [
        "ffsubsync",
        extracted_subtitle_file if extracted_sub_exists else video_file,
        "-i", unsynchronized_sub,
        "-o", synchronized_sub
    ]

    # Start ffsubsync as a subprocess, capturing stdout (and stderr merged)
    config.global_sync_process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1  # Line-buffered
    )

    # Function to read output and update global_progress
    def read_output():
        for line in iter(config.global_sync_process.stdout.readline, ''):
            print(line.strip())
            match = re.search(r"(\d+)%", line)
            if match:
                config.global_progress = match.group(1)
        config.global_sync_process.stdout.close()

    # Start the output reader in a background thread
    thread = threading.Thread(target=read_output, daemon=True)
    thread.start()

    # Wait for ffsubsync to finish
    config.global_sync_process.wait()

    return config.global_sync_process.returncode == 0


def sync_with_fixed_offset(synchronized_sub, unsynchronized_sub, offset):
    subs = pysubs2.load(unsynchronized_sub)
    subs.shift(ms=offset * 1000)
    subs.save(synchronized_sub)
    return True
