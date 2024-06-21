import os
import requests
from flask import Flask, render_template, request, jsonify, session
from bs4 import BeautifulSoup

app = Flask(__name__)

BASE_URL = "https://rargb.to/"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# qBittorrent configuration from environment variables
QBITTORRENT_BASE_URL = os.getenv('QBITTORRENT_BASE_URL')
QBITTORRENT_API_LOGIN = "/api/v2/auth/login"
QBITTORRENT_API_ADD_TORRENT = "/api/v2/torrents/add"
QBITTORRENT_USERNAME = os.getenv('QBITTORRENT_USERNAME')
QBITTORRENT_PASSWORD = os.getenv('QBITTORRENT_PASSWORD')

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
        if len(columns) > 6:  # Ensure there are enough columns
            title_column = columns[1].select_one("a")
            if title_column:
                title = title_column.text
                link = BASE_URL + title_column['href']
                category = columns[2].text.strip()
                if category in ["Movies/Bollywood", "Movies/Dubs/Dual Audio", "XXX/Video"]:
                    continue
                size = columns[4].text
                seeders = int(columns[5].text)  # Convert to integer for sorting
                leechers = columns[6].text
                date_uploaded = columns[3].text

                torrents.append({
                    "title": title,
                    "link": link,
                    "category": category,
                    "size": size,
                    "seeders": seeders,
                    "leechers": leechers,
                    "date_uploaded": date_uploaded
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

def login_to_qbittorrent():
    global session
    login_url = QBITTORRENT_BASE_URL + QBITTORRENT_API_LOGIN
    login_data = {
        'username': QBITTORRENT_USERNAME,
        'password': QBITTORRENT_PASSWORD
    }
    response = session.post(login_url, data=login_data)
    if response.status_code == 200:
        print("Logged in to qBittorrent successfully.")
        return True
    else:
        print(f"Failed to log in to qBittorrent. Status code: {response.status_code}")
        return False

def add_torrent_to_qbittorrent(magnet_link):
    global session
    add_torrent_url = QBITTORRENT_BASE_URL + QBITTORRENT_API_ADD_TORRENT
    data = {
        'urls': magnet_link
    }
    response = session.post(add_torrent_url, data=data)
    if response.status_code == 200:
        print("Torrent added successfully to qBittorrent.")
        return True
    else:
        print(f"Failed to add torrent to qBittorrent. Status code: {response.status_code}")
        return False

@app.route('/')
def home():
    search_query = request.args.get('search', '')
    page = request.args.get('page', default=1, type=int)

    if search_query:
        torrents = search_torrents(search_query)
        # Sort torrents by seeders descending
        torrents.sort(key=lambda x: x['seeders'], reverse=True)
    else:
        page_url = f"{BASE_URL}movies/{page}/"
        html_content = fetch_html(page_url)
        if html_content:
            torrents = parse_html(html_content)
        else:
            torrents = []

    return render_template('index.html', torrents=torrents, page=page, search_query=search_query)

@app.route('/get_magnet_link', methods=['POST'])
def get_magnet_link():
    torrent_url = request.json.get('torrent_url')
    magnet_link = fetch_magnet_link(torrent_url)
    if magnet_link:
        success = add_torrent_to_qbittorrent(magnet_link)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to add torrent to qBittorrent.'}), 500
    else:
        return jsonify({'success': False, 'error': 'Failed to fetch magnet link.'}), 400

def search_torrents(query):
    search_url = f"https://rargb.to/search/?search={query}"
    html_content = fetch_html(search_url)
    if html_content:
        return parse_html(html_content)
    else:
        return []

if __name__ == "__main__":
    session = requests.Session()
    logged_in = login_to_qbittorrent()
    if logged_in:
        app.run(host='0.0.0.0', port=8888)
    else:
        print("Failed to login to qBittorrent. Exiting.")
