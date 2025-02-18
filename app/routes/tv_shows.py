import requests
from flask import Blueprint, jsonify, request

from app.services import tmdb_service
from app.services.config import TMDB_BASE_URL, TMDB_KEY
from app.services.tmdb_service import get_top_rated_shows, get_trending_shows, get_tv_watchlist, \
    get_popular_running_shows, search_tv_shows_by_name

tv_shows_bp = Blueprint("tv_shows", __name__, url_prefix="")


@tv_shows_bp.route("/api/tv", methods=["GET"])
def home_tv():
    page = request.args.get('page', default=1, type=int)
    sort = request.args.get('sort', default='popular', type=str)

    if sort == 'top-rated':
        shows, total_pages = get_top_rated_shows(page)
    elif sort == 'trending':
        shows, total_pages = get_trending_shows(page)
    elif sort == 'watchlist':
        shows, total_pages = get_tv_watchlist(page)
    else:
        shows, total_pages = get_popular_running_shows(page)
    return jsonify({
        'movies': shows,
        'page': page,
        'total_pages': total_pages
    })


@tv_shows_bp.route("/api/tv/<int:show_id>", methods=["GET"])
def show_detail(show_id):
    # Fetch show details
    show_data = tmdb_service.get_tv_show_details(show_id)
    params = {'api_key': TMDB_KEY}

    # Fetch seasons and episodes
    seasons = show_data.get('seasons', [])
    seasons = [season for season in seasons if season.get('season_number') != 0]  # Filter out season 0

    vote_average = show_data.get('vote_average', 0)
    user_score_percentage = round(vote_average * 10)

    for season in seasons:
        season_number = season.get('season_number')
        episodes_url = f"{TMDB_BASE_URL}/tv/{show_id}/season/{season_number}"
        episodes_response = requests.get(episodes_url, params=params)
        episodes_data = episodes_response.json()
        season['episodes'] = [episode['episode_number'] for episode in episodes_data.get('episodes', [])]

    show = {
        'name': show_data.get('name'),
        'release_date': show_data.get('first_air_date'),
        'poster_path': show_data.get('poster_path'),
        'overview': show_data.get('overview'),
        'genre': ', '.join([genre['name'] for genre in show_data.get('genres', [])]),
        'cast': ', '.join([member['name'] for member in show_data.get('credits', {}).get('cast', [])[:5]]),
        'user_score_percentage': user_score_percentage
    }

    return jsonify({
        'title': show,
        'seasons': seasons
    })


@tv_shows_bp.route("/api/tv/search", methods=["GET"])
def search_tv_shows():
    query = request.args.get('query', '')
    page = request.args.get('page', 1)
    response = []
    if query:
        response = search_tv_shows_by_name(query, page)
    return jsonify({
        'page': response.get('page'),
        'total_pages': response.get('total_pages'),
        'movies': response.get('results')
    })
