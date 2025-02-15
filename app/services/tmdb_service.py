import logging

import requests
from app.services.config import TMDB_BASE_URL, TMDB_KEY
from app.services.subtitle_service import caching_json
from app.services.utils import normalize_str

tmdb_session = requests.Session()


def get_popular_bluray_movies(page):
    url = f"{TMDB_BASE_URL}/discover/movie"
    params = {
        'api_key': TMDB_KEY,
        'sort_by': 'popularity.desc',
        'with_release_type': 5,
        'page': page
    }
    response = requests.get(url, params=params)
    data = response.json()
    total_pages = data.get('total_pages', 1)
    return data['results'], total_pages


def get_top_rated_movies(page):
    url = f"{TMDB_BASE_URL}/movie/top_rated"
    params = {
        'api_key': TMDB_KEY,
        'page': page
    }
    response = requests.get(url, params=params)
    data = response.json()
    total_pages = data.get('total_pages', 1)
    return data['results'], total_pages


def get_trending_movies(page):
    url = f"{TMDB_BASE_URL}/trending/movie/day?language=en-US"
    params = {
        'api_key': TMDB_KEY,
        'page': page
    }
    response = requests.get(url, params=params)
    data = response.json()
    total_pages = data.get('total_pages', 1)
    return data['results'], total_pages


def get_movie_watchlist(page):
    session_id = tmdb_session.get('tmdb_session_id')
    url = f'{TMDB_BASE_URL}/account/21427229/watchlist/movies?language=en-US&page=1&sort_by=created_at.asc'
    params = {
        'api_key': TMDB_KEY,
        'page': page,
        'session_id': session_id
    }
    response = requests.get(url, params=params)
    data = response.json()
    total_pages = data.get('total_pages', 1)
    return data['results'], total_pages


def get_tv_watchlist(page):
    session_id = tmdb_session.get('tmdb_session_id')
    url = f'{TMDB_BASE_URL}/account/21427229/watchlist/tv?language=en-US&page=1&sort_by=created_at.asc'
    params = {
        'api_key': TMDB_KEY,
        'page': page,
        'session_id': session_id
    }
    response = requests.get(url, params=params)
    data = response.json()
    total_pages = data.get('total_pages', 1)
    return data['results'], total_pages


def toggle_item_watchlist(media_type, action, title_id):
    watchlist = True
    if action == 'remove':
        watchlist = False

    session_id = tmdb_session.get('tmdb_session_id')
    url = f'{TMDB_BASE_URL}/account/21427229/watchlist'
    params = {
        'api_key': TMDB_KEY,
        'session_id': session_id
    }
    payload = {
        "media_type": media_type,
        "media_id": title_id,
        "watchlist": watchlist
    }

    try:
        response = requests.post(url, json=payload, params=params)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"Error toggling watchlist item: {e}")
        return False


def init_movie_watchlist_ids():
    tmdb_session['movie_watchlist_ids'] = []

    page = 1
    while True:
        movies, total_pages = get_movie_watchlist(page)
        if not movies:
            break
        tmdb_session['movie_watchlist_ids'].extend([movie['id'] for movie in movies])
        if page >= total_pages:
            break
        page += 1

    return tmdb_session['movie_watchlist_ids']


def init_tv_watchlist_ids():
    tmdb_session['tv_watchlist_ids'] = []

    page = 1
    while True:
        tv_shows, total_pages = get_tv_watchlist(page)
        if not tv_shows:
            break
        tmdb_session['tv_watchlist_ids'].extend([show['id'] for show in tv_shows])
        if page >= total_pages:
            break
        page += 1

    return tmdb_session['tv_watchlist_ids']


def get_trending_shows(page):
    url = f"{TMDB_BASE_URL}/trending/tv/day?language=en-US"
    params = {
        'api_key': TMDB_KEY,
        'page': page
    }
    response = requests.get(url, params=params)
    data = response.json()
    total_pages = data.get('total_pages', 1)
    return data['results'], total_pages


def get_popular_running_shows(page):
    url = f"{TMDB_BASE_URL}/trending/tv/week"
    params = {
        'api_key': TMDB_KEY,
        'page': page
    }
    response = requests.get(url, params=params)
    data = response.json()
    total_pages = data.get('total_pages', 1)
    return data['results'], total_pages


def get_top_rated_shows(page):
    url = f"{TMDB_BASE_URL}/tv/top_rated"
    params = {
        'api_key': TMDB_KEY,
        'page': page
    }
    response = requests.get(url, params=params)
    data = response.json()
    total_pages = data.get('total_pages', 1)
    return data['results'], total_pages


def get_movie_details(movie_id):
    url = f"{TMDB_BASE_URL}/movie/{movie_id}"
    params = {'api_key': TMDB_KEY}
    response = requests.get(url, params=params)
    return response.json()


def search_movies_by_name(query, page):
    url = f'https://api.themoviedb.org/3/search/movie'
    params = {
        'api_key': TMDB_KEY,
        'query': query,
        'language': 'en-US',
        'page': page,
        'include_adult': False
    }
    response = requests.get(url, params=params)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: Unable to fetch movies from TMDb. Status code: {response.status_code}")
        return []


def search_tv_shows_by_name(query, page):
    url = f'https://api.themoviedb.org/3/search/tv'
    params = {
        'api_key': TMDB_KEY,
        'query': query,
        'language': 'en-US',
        'page': page
    }
    response = requests.get(url, params=params)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: Unable to fetch TV shows from TMDb. Status code: {response.status_code}")
        return []


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
