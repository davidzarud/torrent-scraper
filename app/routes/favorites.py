import sqlite3

from flask import Blueprint, request, jsonify

favorites_bp = Blueprint("favorites", __name__, url_prefix="")


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
        cursor.execute(f"INSERT INTO favorites (id, title, type, poster_path) VALUES (?, ?, ?, ?)", (tmdb_id, title, media_type, poster_path))
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

        return jsonify([{"id": favorite[0], "title": favorite[1], "type": favorite[2], "poster_path": favorite[3]} for favorite in favorites]), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 400


init_db()
