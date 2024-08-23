import logging

import requests

from config import HEADERS, RARBG_BASE_URL
from bs4 import BeautifulSoup

from services.utils import sanitize_string


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
                link = RARBG_BASE_URL + title_column['href']
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


def search_torrents(query):
    logging.info(f"Searching torrents with query: {query}")
    all_torrents = []
    query = sanitize_string(query)
    for page in range(1, 4):  # Fetch results from the first 3 pages
        search_url = f"{RARBG_BASE_URL}search/{page}/?search={query}"
        html_content = fetch_html(search_url)
        if html_content:
            all_torrents.extend(parse_html(html_content))
        else:
            break

    # Sort torrents by the number of seeders in descending order
    all_torrents.sort(key=lambda torrent: torrent['seeders'], reverse=True)
    print("torrs ", all_torrents)
    return all_torrents
