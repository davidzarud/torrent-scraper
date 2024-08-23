import re

import unicodedata


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
