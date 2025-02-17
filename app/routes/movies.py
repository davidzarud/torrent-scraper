import requests
from flask import Blueprint, jsonify, request

from app.services import tmdb_service
from app.services.config import TMDB_BASE_URL, TMDB_KEY
from app.services.html_service import search_torrents
from app.services.tmdb_service import get_popular_bluray_movies, get_trending_movies, get_movie_watchlist, \
    get_top_rated_movies, search_movies_by_name

movies_bp = Blueprint("movies", __name__, url_prefix="")


@movies_bp.route("/api/movies", methods=["GET"])
def get_movies():
    page = request.args.get('page', default=1, type=int)
    sort = request.args.get('sort', default='popular', type=str)

    if sort == 'popular':
        movies_result, total_pages = get_popular_bluray_movies(page)
    elif sort == 'trending':
        movies_result, total_pages = get_trending_movies(page)
    elif sort == 'watchlist':
        movies_result, total_pages = get_movie_watchlist(page)
    else:
        movies_result, total_pages = get_top_rated_movies(page)

    # Return the movies result and optionally the total pages.
    return jsonify({
        'movies': movies_result,
        'page': page,
        'total_pages': total_pages
    })


@movies_bp.route("/api/movie/<int:movie_id>", methods=["GET"])
def movie_detail(movie_id):

    movie_data = tmdb_service.get_movie_details(movie_id)

    genres = [genre['name'] for genre in movie_data.get('genres', [])]
    genre_string = ', '.join(genres)

    credits_data = tmdb_service.get_movie_credits(movie_id)
    cast = [member['name'] for member in credits_data.get('cast', [])[:5]]
    cast_string = ', '.join(cast)

    vote_average = movie_data.get('vote_average', 0)
    user_score_percentage = round(vote_average * 10)

    movie = {
        'title': movie_data.get('title'),
        'release_date': movie_data.get('release_date'),
        'poster_path': movie_data.get('poster_path'),
        'overview': movie_data.get('overview'),
        'genre': genre_string,
        'cast': cast_string,
        'user_score_percentage': user_score_percentage
    }

    torrents = search_torrents(f"{movie_data.get('title')} {movie_data.get('release_date')[:4]}")
    return jsonify({
        'title': movie,
        'torrents': torrents
    })


@movies_bp.route("/api/movies/search", methods=["GET"])
def search_movies():
    query = request.args.get('query', '')
    page = request.args.get('page', 1)
    response = []
    if query:
        response = search_movies_by_name(query, page)
    return jsonify({
        'page': response.get('page'),
        'total_pages': response.get('total_pages'),
        'movies': response.get('results')
    })
