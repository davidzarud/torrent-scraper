import logging

import requests

from app.services.config import TMDB_BASE_URL, TMDB_KEY, MOVIE_GENRE_MAP, TV_GENRE_MAP, NETWORK_ID_MAP
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


def get_movie_credits(movie_id):
    credits_url = f"{TMDB_BASE_URL}/movie/{movie_id}/credits"
    params = {'api_key': TMDB_KEY}
    credits_response = requests.get(credits_url, params=params)
    return credits_response.json()


def get_tv_show_details(show_id):
    url = f"{TMDB_BASE_URL}/tv/{show_id}?append_to_response=credits"
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
        'include_adult': True
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
        'page': page,
        'include_adult': True
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


def advanced_search(args, context):
    page = args.get('page')
    from_date = args.get('from_date')
    to_date = args.get('to_date')
    rating_min = args.get('rating_min')
    rating_max = args.get('rating_max')
    genres = args.get('genres')
    providers = args.get('providers')

    url = f'https://api.themoviedb.org/3/discover/{context}'
    params = {
        'api_key': TMDB_KEY,
        'page': page,
        'include_adult': True,
        'sort_by': 'popularity.desc'
    }

    if context == 'movie':
        optional_params = {
            'primary_release_date.gte': from_date,
            'primary_release_date.lte': to_date,
            'vote_average.gte': rating_min,
            'vote_average.lte': rating_max,
            'with_genres': map_to_list(genres, MOVIE_GENRE_MAP)
        }
    else:
        optional_params = {
            'first_air_date.gte': from_date,
            'first_air_date.lte': to_date,
            'vote_average.gte': rating_min,
            'vote_average.lte': rating_max,
            'with_genres': map_to_list(genres, TV_GENRE_MAP),
            'with_networks': map_to_list(providers, NETWORK_ID_MAP)
        }

    params.update({k: v for k, v in optional_params.items() if v is not None})
    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        total_pages = data.get('total_pages', 1)
        return data['results'], total_pages
    else:
        print(f"Error: Unable to fetch TV shows from TMDb. Status code: {response.status_code}")
        return [], 1


def map_to_list(str_list, id_map):
    if str_list is None or str_list == '':
        return None

    genres_list = [genre.strip() for genre in str_list.split(",")]  # Split and trim spaces
    genre_ids = [str(id_map[genre]) for genre in genres_list if genre in id_map]
    return "|".join(genre_ids)
