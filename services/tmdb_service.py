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