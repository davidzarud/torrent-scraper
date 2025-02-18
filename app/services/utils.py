import logging
import os
import platform
import re

import unicodedata

is_windows = platform.system() == 'Windows'


def normalize_str(s):
    normalized = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in normalized if not unicodedata.combining(c))


def sanitize_string(query):
    # Normalize the string to NFKD (decomposes characters, e.g., é -> e + ́ )
    normalized_query = unicodedata.normalize('NFKD', query)

    # Encode to ASCII, ignoring non-ASCII characters, then decode back to a string
    sanitized_query = normalized_query.encode('ascii', 'ignore').decode('ascii')

    # Replace apostrophes with an empty string
    sanitized_query = sanitized_query.replace("'", "")
    sanitized_query = sanitized_query.replace("&", "")

    return sanitized_query


def extract_season_episode(title):
    match = re.search(r's(\d{2})e(\d{2})', title, re.IGNORECASE)
    if match:
        season = match.group(1)
        episode = match.group(2)
        return season, episode
    return None, None


def unescape_html(text):
    """Escape &, <, > as well as single and double quotes for HTML."""
    return text.replace('&amp;', '&'). \
        replace('&quot;', '"'). \
        replace('&#39;', "'")


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
        logging.error(f"Directory '{target_dir}' does not exist.")
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
