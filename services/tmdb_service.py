import logging

import requests

from config import TMDB_BASE_URL, TMDB_KEY


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
    from app import tmdb_session
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
    from app import tmdb_session
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
    from app import tmdb_session
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
    from app import tmdb_session
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
    from app import tmdb_session
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


def is_tmdb_session_valid():
    from app import tmdb_session
    session_id = tmdb_session.get('tmdb_session_id')
    if not session_id:
        return False

    url = f'https://api.themoviedb.org/3/account?api_key={TMDB_KEY}&session_id={session_id}'
    response = requests.get(url)
    return response.status_code == 200


def get_movie_details(movie_id):
    url = f"{TMDB_BASE_URL}/movie/{movie_id}"
    params = {'api_key': TMDB_KEY}
    response = requests.get(url, params=params)
    return response.json()


def search_movies_by_name(query):
    url = f'https://api.themoviedb.org/3/search/movie'
    params = {
        'api_key': TMDB_KEY,
        'query': query,
        'language': 'en-US',
        'page': 1,
        'include_adult': False
    }
    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        return data.get('results', [])
    else:
        print(f"Error: Unable to fetch movies from TMDb. Status code: {response.status_code}")
        return []


def search_tv_shows_by_name(query):
    url = f'https://api.themoviedb.org/3/search/tv'
    params = {
        'api_key': TMDB_KEY,
        'query': query,
        'language': 'en-US',
        'page': 1
    }
    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        return data.get('results', [])
    else:
        print(f"Error: Unable to fetch TV shows from TMDb. Status code: {response.status_code}")
        return []
