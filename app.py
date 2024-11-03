import re
from os import makedirs

from flask import Flask, render_template, request, jsonify, redirect, url_for, session as tmdb_session

from config import *
from services.html_service import search_torrents, fetch_magnet_link
from services.qbittorrent_service import add_torrent_to_qbittorrent
from services.tmdb_service import *
from subs import search, download_subtitle

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.add_url_rule('/search_sub', view_func=search, methods=['POST'])
app.add_url_rule('/download/<int:sub_id>/<string:name>', view_func=download_subtitle, methods=['POST'])

session = requests.Session()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


@app.route('/')
def home():
    return redirect(url_for('movies', sort='trending'))


@app.route('/tmdb-auth/<sort>')
def tmdb_auth(sort):
    request_token_url = "https://api.themoviedb.org/3/authentication/token/new"
    params = {"api_key": TMDB_KEY}
    response = requests.get(request_token_url, params=params)
    request_token = response.json()['request_token']

    auth_url = (f'https://www.themoviedb.org/authenticate/{request_token}'
                f'?redirect_to={url_for("tmdb_callback", _external=True, sort=sort)}')
    tmdb_session['request_token'] = request_token  # Store the request token in session
    return redirect(auth_url)


@app.route('/tmdb-callback/<sort>')
def tmdb_callback(sort):
    request_token = tmdb_session['request_token']
    create_session_id_url = "https://api.themoviedb.org/3/authentication/session/new"
    params = {'api_key': TMDB_KEY}
    data = {'request_token': request_token}

    response = requests.post(create_session_id_url, json=data, params=params)
    session_id = response.json().get('session_id')

    if session_id:
        tmdb_session['tmdb_session_id'] = session_id  # Store the session_id in Flask session
        return redirect(url_for('movies', sort=sort))
    else:
        return "Failed to create session ID", 400


@app.route('/movies')
def movies():
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
    return render_template('movies.html', movies=movies_result, page=page, total_pages=total_pages)


@app.route('/movie/<int:movie_id>')
def movie_detail(movie_id):
    url = f"{TMDB_BASE_URL}/movie/{movie_id}"
    params = {'api_key': TMDB_KEY}
    response = requests.get(url, params=params)
    movie_data = response.json()

    genres = [genre['name'] for genre in movie_data.get('genres', [])]
    genre_string = ', '.join(genres)

    credits_url = f"{TMDB_BASE_URL}/movie/{movie_id}/credits"
    credits_response = requests.get(credits_url, params=params)
    credits_data = credits_response.json()
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

    return render_template('movie_detail.html', movie=movie, torrents=torrents)


@app.route('/search_movies')
def search_movies():
    query = request.args.get('query', '')
    if query:
        movies_result = search_movies_by_name(query)
        return render_template('movies.html', movies=movies_result, page=1, total_pages=1)
    return render_template('movies.html', movies=[], page=1, total_pages=1)


@app.route('/tv')
def home_tv():
    page = request.args.get('page', default=1, type=int)
    sort = request.args.get('sort', default='popular', type=str)

    if sort == 'top_rated':
        shows, total_pages = get_top_rated_shows(page)
    elif sort == 'trending':
        shows, total_pages = get_trending_shows(page)
    elif sort == 'watchlist':
        shows, total_pages = get_tv_watchlist(page)
    else:
        shows, total_pages = get_popular_running_shows(page)
    return render_template('tv_shows.html', shows=shows, page=page, total_pages=total_pages)


@app.route('/show/<int:show_id>')
def show_detail(show_id):
    # Fetch show details
    url = f"{TMDB_BASE_URL}/tv/{show_id}?append_to_response=credits"
    params = {'api_key': TMDB_KEY}
    response = requests.get(url, params=params)
    show_data = response.json()

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

    return render_template('show_detail.html', show=show, seasons=seasons)


@app.route('/search_tv_shows')
def search_tv_shows():
    query = request.args.get('query', '')
    if query:
        shows_result = search_tv_shows_by_name(query)
        return render_template('tv_shows.html', shows=shows_result, page=1, total_pages=1)
    return render_template('tv_shows.html', shows=[], page=1, total_pages=1)


@app.route('/get_magnet_link', methods=['POST'])
def get_magnet_link():
    data = request.get_json()
    torrent_url = data.get('torrent_url')
    context = data.get('context')
    title = re.sub(r'[<>:"/\\|?*]', '', data.get('title'))
    magnet_link = fetch_magnet_link(torrent_url)
    if magnet_link:
        success = add_torrent_to_qbittorrent(magnet_link, context, title)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to add torrent to qBittorrent'})
    else:
        return jsonify({'success': False, 'error': 'Failed to fetch magnet link'})


@app.route('/tmdb/watchlist/<media_type>/<action>/<title_id>', methods=['POST'])
def toggle_watchlist(media_type, action, title_id):
    success = toggle_item_watchlist(media_type, action, title_id)
    if success:
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Failed to toggle watchlist item'})


@app.route('/search_torrents')
def search_torrents_route():
    query = request.args.get('query')
    if query:
        torrents = search_torrents(query)
        return jsonify({'torrents': torrents})
    return jsonify({'torrents': []})


if __name__ == '__main__':
    makedirs(TMP_DIR, exist_ok=True)
    makedirs(SUBS_DIR, exist_ok=True)
    app.run(debug=True)
