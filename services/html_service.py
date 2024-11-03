import logging
import re

import requests
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz

from config import HEADERS, RARBG_BASE_URL
from services.utils import sanitize_string


def fetch_html(url):
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        return response.text
    else:
        print(f"Failed to retrieve content: {response.status_code}")
        return None


def fetch_magnet_link(torrent_url):
    html_content = fetch_html(torrent_url)
    if html_content:
        soup = BeautifulSoup(html_content, 'lxml')
        magnet_link = soup.select_one('a[href^="magnet:?"]').get('href')
        return magnet_link
    else:
        return None


def search_torrents_rarbg(query):
    logging.info(f"Searching rarbg torrents with query: {query}")
    all_torrents = []
    query = sanitize_string(query)
    for page in range(1, 4):  # Fetch results from the first 3 pages
        search_url = f"{RARBG_BASE_URL}search/{page}/?search={query}"
        html_content = fetch_html(search_url)
        if html_content:
            all_torrents.extend(parse_rarbg_html(html_content))
        else:
            break

    # Sort torrents by the number of seeders in descending order
    all_torrents.sort(key=lambda torrent: torrent['seeders'], reverse=True)
    return all_torrents


def parse_rarbg_html(html):
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


def search_torrents_yts(query):
    logging.info(f"Searching yts torrents with query: {query}")
    all_torrents = []
    query = sanitize_string(query)
    search_url = f"https://yts.mx/browse-movies/{query}/all/all/0/latest/0/all"
    html_content = fetch_html(search_url)
    if html_content:
        movie_link = get_yts_link(html_content, query)
        soup = BeautifulSoup(movie_link, "lxml")


def get_yts_link(html, query):
    soup = BeautifulSoup(html, 'lxml')
    match = re.match(r"(.+?)\s(\d{4})$", query)
    if match:
        movie_name = match.group(1).strip()  # The name part
        movie_year = match.group(2)  # The year part
    else:
        print("No match found.")
        return None

    movie_url = None
    best_match = 0
    movie_links = soup.find_all('a', class_='browse-movie-title')
    for movie_link in movie_links:
        movie_title = movie_link.text.strip()
        similarity = fuzz.ratio(movie_name, movie_title)
        year_element = movie_link.find_next('div', class_='browse-movie-year')
        if similarity > best_match and year_element.text.strip() == movie_year:
            best_match = similarity
            movie_url = movie_link['href']
    return movie_url
