import os
import sqlite3

import google.generativeai as genai
from flask import Blueprint, request, jsonify

from app.routes.movies import movie_detail
from app.services import tmdb_service

favorites_bp = Blueprint("favorites", __name__, url_prefix="")

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))  # Store API key in env variables


def init_db():
    conn = sqlite3.connect('favorites.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS favorites
                      (id BIGINT PRIMARY KEY, title TEXT, type TEXT, poster_path TEXT)''')
    conn.commit()
    conn.close()


@favorites_bp.route('/api/favorites', methods=['POST'])
def add_favorite():
    try:
        data = request.get_json()
        tmdb_id = data['id']
        title = data['title']
        media_type = data['type']
        poster_path = data['poster_path']

        conn = sqlite3.connect('favorites.db')

        cursor = conn.cursor()
        cursor.execute(f"INSERT INTO favorites (id, title, type, poster_path) VALUES (?, ?, ?, ?)",
                       (tmdb_id, title, media_type, poster_path))
        conn.commit()
        conn.close()

        return jsonify({"message": "Movie added to favorites"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@favorites_bp.route('/api/favorites/<int:tmdb_id>', methods=['DELETE'])
def remove_favorite(tmdb_id):
    try:
        conn = sqlite3.connect('favorites.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM favorites WHERE id = ?", (tmdb_id,))
        conn.commit()
        conn.close()

        return jsonify({"message": "Movie removed from favorites"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@favorites_bp.route('/api/favorites', methods=['GET'])
def get_favorites():
    try:
        conn = sqlite3.connect('favorites.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, type, poster_path FROM favorites")
        favorites = cursor.fetchall()
        conn.close()

        return jsonify(
            [{"id": favorite[0], "title": favorite[1], "type": favorite[2], "poster_path": favorite[3]} for favorite in
             favorites]), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400


@favorites_bp.route('/api/recommendations/<int:tmdb_id>', methods=['GET'])
def get_recommendations(tmdb_id):
    type = request.args.get('type')
    if type == 'movies':
        title = tmdb_service.get_movie_details(tmdb_id).get('title')
        type = "movie"
    else:
        title = tmdb_service.get_tv_show_details(tmdb_id).get('name')
        type = "tv show"
    try:
        model = genai.GenerativeModel("gemini-pro")
        prompt = (
            f"You now assume a role of a movie and tv show expert. Based on the {type} {title} suggest 20 movies and 20 tv "
            f"shows that i might like if i like this title. List movies first with each movie in its own row. "
            f"surround each movie with *** at the beginning and at the end. Underneath that list tv shows with "
            f"each tv show in its own row. surround each tv show with *** at the beginning and at the end.")

        response = model.generate_content(prompt)

        recommendations = response.text

        # Parsing Gemini response
        movies_list, tv_shows_list = split_movies_tvshows(recommendations)

        recommended_tv_shows, recommended_movies = [], []
        for movie in movies_list:
            tmdb_movie = tmdb_service.search_movies_by_name(movie, None)
            if tmdb_movie and tmdb_movie.get('results'):
                recommended_movie = tmdb_movie.get('results')[0]
                recommended_movies.append({'id': recommended_movie.get('id'),
                                           'title': recommended_movie.get('title'),
                                           'imageUrl': 'https://image.tmdb.org/t/p/w92' + recommended_movie.get('poster_path')})

        for tv_show in tv_shows_list:
            tmdb_tv_show = tmdb_service.search_tv_shows_by_name(tv_show, 1)
            if tmdb_tv_show and tmdb_tv_show.get('results'):
                recommended_tv_show = tmdb_tv_show.get('results')[0]
                recommended_tv_shows.append({'id': recommended_tv_show.get('id'),
                                         'title': recommended_tv_show.get('name'),
                                         'imageUrl': 'https://image.tmdb.org/t/p/w92' + recommended_tv_show.get('poster_path')})

        return jsonify({"movies": recommended_movies, "shows": recommended_tv_shows})

    except Exception as e:
        return jsonify({"movies": [], "shows": []})


def split_movies_tvshows(text):
    lines = text.strip().split("\n")  # Split by newlines
    movies, tv_shows = [], []
    current_category = None

    for line in lines:
        line = line.strip()

        if "***Movies***" in line:
            current_category = "movies"
        elif "***TV Shows***" in line:
            current_category = "tv_shows"
        elif line:  # Avoid empty lines
            if current_category == "movies":
                movies.append(line.strip("*"))  # Remove *** formatting
            elif current_category == "tv_shows":
                tv_shows.append(line.strip("*"))

    return movies, tv_shows


init_db()
