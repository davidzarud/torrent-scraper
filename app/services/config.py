import os

global_progress = "0"
global_sync_process = None

ffmpeg_path = os.getenv('FFMPEG_PATH', 'ffmpeg')  # Default to 'ffmpeg' if not set

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/91.0.4472.124 Safari/537.36'
}

MEDIA_EXTENSIONS = {
    # Video formats
    '.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v',
    '.mpeg', '.mpg', '.mts', '.m2ts', '.ts', '.vob', '.3gp', '.3g2',
    # Audio formats
    '.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a', '.opus',
    # Additional formats
    '.ogv', '.mxf', '.rmvb', '.asf', '.divx'
}

MOVIE_GENRE_MAP = {"Action": 28, "Adventure": 12, "Animation": 16, "Comedy": 35, "Crime": 80, "Documentary": 99,
                   "Drama": 18, "Family": 10751, "Fantasy": 14, "History": 36, "Horror": 27, "Music": 10402,
                   "Mystery": 9648, "Romance": 10749, "Science Fiction": 878, "Thriller": 53, "War": 10752,
                   "Western": 37}
TV_GENRE_MAP = {'Action & Adventure': 10759, 'Animation': 16, 'Comedy': 35, 'Crime': 80, 'Documentary': 99, 'Drama': 18,
                'Family': 10751, 'Kids': 10762, 'Mystery': 9648, 'News': 10763, 'Reality': 10764,
                'Sci-Fi & Fantasy': 10765, 'Soap': 10766, 'Talk': 10767, 'War & Politics': 10768, 'Western': 37}
NETWORK_ID_MAP = {'Netflix': 213, 'HBO': 3186, 'Disney Plus': 2739, 'Apple TV': 2552, 'Amazon Prime': 1024}

TMDB_BASE_URL = os.getenv('TMDB_BASE_URL')
TMDB_KEY = os.getenv('TMDB_KEY')
QBITTORRENT_BASE_URL = os.getenv('QBITTORRENT_BASE_URL')
QBITTORRENT_USERNAME = os.getenv('QBITTORRENT_USERNAME')
QBITTORRENT_PASSWORD = os.getenv('QBITTORRENT_PASSWORD')
JELLYFIN_BASE_URL = os.getenv('JELLYFIN_BASE_URL')
JELLYFIN_API_KEY = os.getenv('JELLYFIN_API_KEY')
RARBG_BASE_URL = "https://rargb.to/"
DOWNLOADS_BASE_PATH = os.getenv('DOWNLOADS_BASE_PATH')
DASH_DIRECTORY = os.getenv('DASH_DIRECTORY')
TMP_DIR = '../../../tmp'
SUBS_DIR = '../../../subs'
WIZDOM_DOMAIN = 'wizdom.xyz/api'
