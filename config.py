import os

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/91.0.4472.124 Safari/537.36'
}

TMDB_BASE_URL = os.getenv('TMDB_BASE_URL')
TMDB_KEY = os.getenv('TMDB_KEY')
QBITTORRENT_BASE_URL = os.getenv('QBITTORRENT_BASE_URL')
QBITTORRENT_USERNAME = os.getenv('QBITTORRENT_USERNAME')
QBITTORRENT_PASSWORD = os.getenv('QBITTORRENT_PASSWORD')
JELLYFIN_BASE_URL = os.getenv('JELLYFIN_BASE_URL')
JELLYFIN_API_KEY = os.getenv('JELLYFIN_API_KEY')
RARBG_BASE_URL = "https://rargb.to/"
SUB_SEARCH_DIR = os.getenv('SUB_SEARCH_DIR')
TMP_DIR = 'tmp'
SUBS_DIR = 'subs'
WIZDOM_DOMAIN = 'wizdom.xyz/api'
