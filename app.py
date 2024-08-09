from flask import Flask, render_template, request, jsonify, redirect, url_for
from requests.exceptions import RequestException
import requests
from bs4 import BeautifulSoup
import logging

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

BASE_URL = "https://rargb.to/"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

TMDB_API_KEY = '6dd8946025483f354ff8987af6cf3980'
TMDB_BASE_URL = 'https://api.themoviedb.org/3'

# QBITTORRENT_BASE_URL = os.getenv('QBITTORRENT_BASE_URL')
# QBITTORRENT_USERNAME = os.getenv('QBITTORRENT_USERNAME')
# QBITTORRENT_PASSWORD = os.getenv('QBITTORRENT_PASSWORD')

QBITTORRENT_BASE_URL = 'http://192.168.1.194:8080'
QBITTORRENT_USERNAME = 'admin'
QBITTORRENT_PASSWORD = 'Dzarud218'

session = requests.Session()


def login_to_qbittorrent():
    login_url = f"{QBITTORRENT_BASE_URL}/api/v2/auth/login"
    data = {
        'username': QBITTORRENT_USERNAME,
        'password': QBITTORRENT_PASSWORD
    }
    try:
        response = session.post(login_url, data=data)
        response.raise_for_status()
        if response.text != "Ok.":
            raise Exception("Failed to login to qBittorrent")
    except RequestException as e:
        print(f"Login error: {e}")
        return False
    return True


qb_cookies = login_to_qbittorrent()


def fetch_html(url):
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.text
    else:
        print(f"Failed to retrieve content: {response.status_code}")
        return None


def parse_html(html):
    soup = BeautifulSoup(html, 'lxml')
    torrents = []

    for row in soup.select("table.lista2t > tr.lista2"):
        columns = row.select("td")
        if len(columns) > 6:
            title_column = columns[1].select_one("a")
            if title_column:
                title = title_column.text
                link = BASE_URL + title_column['href']
                category = columns[2].text.strip()
                if category in ["Movies/Bollywood", "Movies/Dubs/Dual Audio", "XXX/Video"]:
                    continue
                size = columns[4].text
                seeders = int(columns[5].text)
                leechers = columns[6].text
                date_uploaded = columns[3].text

                torrents.append({
                    "title": title,
                    "link": link,
                    "category": category,
                    "size": size,
                    "seeders": seeders,
                    "leechers": leechers,
                    "date_uploaded": date_uploaded,
                    "imdb_link": None  # Initially, set IMDb link to None
                })

    return torrents


def fetch_magnet_link(torrent_url):
    html_content = fetch_html(torrent_url)
    if html_content:
        soup = BeautifulSoup(html_content, 'lxml')
        magnet_link = soup.select_one('a[href^="magnet:?"]').get('href')
        return magnet_link
    else:
        return None


def add_torrent_to_qbittorrent(magnet_link, context):
    if not QBITTORRENT_BASE_URL or not QBITTORRENT_USERNAME or not QBITTORRENT_PASSWORD:
        print("qBittorrent credentials not set.")
        return False

    if not is_session_valid():
        if not login_to_qbittorrent():
            print("Failed to login to qBittorrent.")
            return False

    add_torrent_url = f"{QBITTORRENT_BASE_URL}/api/v2/torrents/add"
    data = {'urls': magnet_link, 'sequentialDownload': 'true', 'firstLastPiecePrio': 'true', 'savepath': context}
    try:
        response = session.post(add_torrent_url, data=data)
        response.raise_for_status()

        return True
    except RequestException as e:
        print(f"Error adding torrent: {e}")
        return False


def is_session_valid():
    try:
        test_url = f"{QBITTORRENT_BASE_URL}/api/v2/auth/login"
        response = session.get(test_url)
        response.raise_for_status()
        if response.text != "Ok.":
            raise Exception("Session is not valid.")
        return True
    except requests.exceptions.RequestException:
        return False


@app.route('/')
def home():
    return redirect(url_for('movies'))


@app.route('/movies')
def movies():
    page = request.args.get('page', default=1, type=int)
    movies, total_pages = get_popular_bluray_movies(page)
    return render_template('movies.html', movies=movies, page=page, total_pages=total_pages)


def get_popular_bluray_movies(page):
    url = f"{TMDB_BASE_URL}/discover/movie"
    params = {
        'api_key': TMDB_API_KEY,
        'sort_by': 'popularity.desc',
        'with_release_type': 5,
        'page': page
    }
    response = requests.get(url, params=params)
    data = response.json()
    total_pages = data.get('total_pages', 1)
    return data['results'], total_pages


def get_popular_running_shows(page):
    url = f"{TMDB_BASE_URL}/trending/tv/week"
    params = {
        'api_key': TMDB_API_KEY,
        'page': page
    }
    response = requests.get(url, params=params)
    data = response.json()
    total_pages = data.get('total_pages', 1)
    return data['results'], total_pages


@app.route('/movie/<int:movie_id>')
def movie_detail(movie_id):
    url = f"{TMDB_BASE_URL}/movie/{movie_id}"
    params = {'api_key': TMDB_API_KEY}
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


def get_movie_details(movie_id):
    url = f"{TMDB_BASE_URL}/movie/{movie_id}"
    params = {'api_key': TMDB_API_KEY}
    response = requests.get(url, params=params)
    return response.json()


@app.route('/show/<int:show_id>')
def show_detail(show_id):
    # Fetch show details
    url = f"{TMDB_BASE_URL}/tv/{show_id}"
    params = {'api_key': TMDB_API_KEY}
    response = requests.get(url, params=params)
    show_data = response.json()

    # Fetch seasons and episodes
    seasons = show_data.get('seasons', [])
    seasons = [season for season in seasons if season.get('season_number') != 0]  # Filter out season 0

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
        'cast': ', '.join([member['name'] for member in show_data.get('credits', {}).get('cast', [])[:5]])
    }

    return render_template('show_detail.html', show=show, seasons=seasons)


@app.route('/tv')
def home_tv():
    page = request.args.get('page', default=1, type=int)
    shows, total_pages = get_popular_running_shows(page)
    return render_template('tvshows.html', shows=shows, page=page, total_pages=total_pages)


@app.route('/get_magnet_link', methods=['POST'])
def get_magnet_link():
    data = request.get_json()
    torrent_url = data.get('torrent_url')
    context = data.get('context')
    magnet_link = fetch_magnet_link(torrent_url)
    if magnet_link:
        success = add_torrent_to_qbittorrent(magnet_link, context)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to add torrent to qBittorrent'})
    else:
        return jsonify({'success': False, 'error': 'Failed to fetch magnet link'})


@app.route('/search_movies')
def search_movies():
    query = request.args.get('query', '')
    if query:
        movies_result = search_movies_by_name(query)
        return render_template('movies.html', movies=movies_result)
    return render_template('movies.html', movies=[], page=1, total_pages=1)


@app.route('/search_tvshows')
def search_tvshows():
    query = request.args.get('query', '')
    if query:
        shows_result = search_tvshows_by_name(query)
        return render_template('tvshows.html', shows=shows_result)
    return render_template('tvshows.html', shows=[], page=1, total_pages=1)


def search_movies_by_name(query):
    url = f'https://api.themoviedb.org/3/search/movie'
    params = {
        'api_key': TMDB_API_KEY,
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


def search_tvshows_by_name(query):
    url = f'https://api.themoviedb.org/3/search/tv'
    params = {
        'api_key': TMDB_API_KEY,
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


@app.route('/search_torrents')
def search_torrents_route():
    query = request.args.get('query')
    if query:
        torrents = search_torrents(query)
        return jsonify({'torrents': torrents})
    return jsonify({'torrents': []})


def search_torrents(query):
    logging.info(f"Searching torrents with query: {query}")
    all_torrents = []
    for page in range(1, 4):  # Fetch results from the first 3 pages
        search_url = f"{BASE_URL}search/{page}/?search={query}"
        html_content = fetch_html(search_url)
        if html_content:
            all_torrents.extend(parse_html(html_content))
        else:
            break

    # Sort torrents by the number of seeders in descending order
    all_torrents.sort(key=lambda torrent: torrent['seeders'], reverse=True)
    return all_torrents


@app.route('/get_imdb_link', methods=['POST'])
def get_imdb_link():
    data = request.get_json()
    torrent_url = data.get('torrent_url')
    if torrent_url:
        torrent_page_html = fetch_html(torrent_url)
        if torrent_page_html:
            soup = BeautifulSoup(torrent_page_html, 'lxml')
            imdb_link_tag = soup.find('a', href=True, text='IMDb')
            if imdb_link_tag:
                imdb_link = imdb_link_tag['href']
                return jsonify({'imdb_link': imdb_link})
    return jsonify({'imdb_link': None})


if __name__ == '__main__':
    app.run(debug=True)
