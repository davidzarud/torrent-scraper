import os
import requests
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, jsonify
from requests.exceptions import RequestException

app = Flask(__name__)

BASE_URL = "https://rargb.to/"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

QBITTORRENT_BASE_URL = os.getenv('QBITTORRENT_BASE_URL')
QBITTORRENT_USERNAME = os.getenv('QBITTORRENT_USERNAME')
QBITTORRENT_PASSWORD = os.getenv('QBITTORRENT_PASSWORD')

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

def add_torrent_to_qbittorrent(magnet_link):
    if not QBITTORRENT_BASE_URL or not QBITTORRENT_USERNAME or not QBITTORRENT_PASSWORD:
        print("qBittorrent credentials not set.")
        return False

    if 'SID' not in session.cookies:
        if not login_to_qbittorrent():
            print("Failed to login to qBittorrent.")
            return False

    add_torrent_url = f"{QBITTORRENT_BASE_URL}/api/v2/torrents/add"
    data = {'urls': magnet_link}
    try:
        response = session.post(add_torrent_url, data=data)
        response.raise_for_status()
        return True
    except RequestException as e:
        print(f"Error adding torrent: {e}")
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
        return jsonify({'success': success})
    else:
        return jsonify({'success': False})

def search_torrents(query):
    search_url = f"https://rargb.to/search/?search={query}"
    html_content = fetch_html(search_url)
    if html_content:
        return parse_html(html_content)
    else:
        return []

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8888)
