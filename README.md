# Torrent Scraper

A self-hosted media management app that lets you browse movies and TV shows, search for torrents, send downloads to qBittorrent, stream media files, and fetch Hebrew subtitles — all from a single web UI.

## Features

- Browse popular, trending, top-rated, and watchlisted movies and TV shows via TMDB
- Search for torrents across torrent indexers
- One-click download — fetches the magnet link and sends it straight to qBittorrent
- In-browser streaming of MP4 files and MKV-to-MP4 remuxing via FFmpeg
- Hebrew subtitle search and download from Wizdom, with automatic SRT → VTT conversion
- Check if a title already exists in your local media library
- Jellyfin library scan triggered automatically after downloads and subtitle imports
- TMDB watchlist integration (add/remove movies and shows)
- Caching layer for TMDB and subtitle API responses

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, Flask |
| Frontend | SPA (pre-built, served as static assets) |
| Database | SQLite (favorites) |
| Torrent Client | qBittorrent (Web API) |
| Media Server | Jellyfin |
| Metadata | TMDB API |
| Subtitles | Wizdom API |
| Streaming | FFmpeg |
| Container | Docker |

## Project Structure

```
torrentScraper/
├── app.py                  # Flask entry point — all API routes
├── config.py               # Environment variables and constants
├── requirements.txt        # Python dependencies
├── Dockerfile
├── docker-compose.yml
├── services/
│   ├── tmdb_service.py     # TMDB API integration
│   ├── html_service.py     # Torrent scraping
│   ├── qbittorrent_service.py  # qBittorrent Web API client
│   ├── jellyfin_service.py # Jellyfin library scan trigger
│   └── utils.py            # String sanitization, helpers
├── static/                 # Pre-built frontend SPA
├── tmp/                    # Cached API responses
└── subs/                   # Temporary subtitle files
```

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/movies` | List movies (popular, trending, top-rated, watchlist) |
| GET | `/api/movie/<id>` | Movie details + torrent results |
| GET | `/api/movies/search` | Search movies by name |
| GET | `/api/tv` | List TV shows |
| GET | `/api/tv/<id>` | Show details with seasons and episodes |
| GET | `/api/tv/search` | Search TV shows by name |
| GET | `/api/search_torrents` | Search torrents by query |
| POST | `/api/get_magnet_link` | Fetch magnet link and add to qBittorrent |
| POST | `/api/search_sub` | Search Hebrew subtitles |
| POST | `/api/download/<sub_id>/<name>` | Download and convert subtitle |
| GET | `/api/title-exists` | Check if media file exists locally |
| GET | `/stream/<title>` | Stream media (MP4 direct / MKV remux) |
| POST | `/tmdb/watchlist/<type>/<action>/<id>` | Add/remove from TMDB watchlist |

## Environment Variables

| Variable | Description | Example |
|---|---|---|
| `TMDB_BASE_URL` | TMDB API base URL | `https://api.themoviedb.org/3` |
| `TMDB_KEY` | TMDB API key | |
| `QBITTORRENT_BASE_URL` | qBittorrent Web UI URL | `http://192.168.1.100:8080` |
| `QBITTORRENT_USERNAME` | qBittorrent username | `admin` |
| `QBITTORRENT_PASSWORD` | qBittorrent password | |
| `JELLYFIN_BASE_URL` | Jellyfin server URL | `http://192.168.1.100:8096` |
| `JELLYFIN_API_KEY` | Jellyfin API key | |
| `DOWNLOADS_BASE_PATH` | Path to downloads directory | `/downloads` |
| `TORRENT_BASE_URL` | Torrent indexer base URL | |

## Deployment

### Prerequisites

- Docker and Docker Compose installed on your server
- A TMDB API key ([get one here](https://www.themoviedb.org/settings/api))
- qBittorrent running with Web UI enabled
- Jellyfin server (optional, for library scan notifications)

### Deploy with Docker Compose

1. Create a directory on your server and add a `docker-compose.yml`:

```yaml
version: "3.8"

services:
  torrent-scraper:
    image: davidzarud/torrent-scraper:latest
    container_name: torrent-scraper
    restart: unless-stopped
    ports:
      - "8888:8888"
    environment:
      - TMDB_BASE_URL=https://api.themoviedb.org/3
      - TMDB_KEY=your_tmdb_api_key
      - QBITTORRENT_BASE_URL=http://192.168.1.100:8080
      - QBITTORRENT_USERNAME=admin
      - QBITTORRENT_PASSWORD=your_password
      - JELLYFIN_BASE_URL=http://192.168.1.100:8096
      - JELLYFIN_API_KEY=your_jellyfin_api_key
      - DOWNLOADS_BASE_PATH=/downloads
      - TORRENT_BASE_URL=https://rargb.to/
    volumes:
      - /path/to/your/downloads:/downloads
```

2. Replace the placeholder values with your actual credentials and paths.

3. Deploy:

```bash
docker compose up -d
```

4. Open `http://your-server-ip:8888` in your browser.

### Deploy via Portainer

1. In Portainer, go to **Stacks** → **Add stack**.
2. Paste the `docker-compose.yml` content above into the web editor.
3. Fill in your environment variables (or use Portainer's env var UI).
4. Click **Deploy the stack**.

The app will be available on port `8888`.

### Updating

Pull the latest image and recreate the container:

```bash
docker compose pull
docker compose up -d
```

In Portainer: open your stack, click **Pull and redeploy**.

## Local Development

```bash
# Clone the repo
git clone https://github.com/davidzarud/torrent-scraper.git
cd torrent-scraper

# Create a virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Copy .env.example to .env and fill in your values
cp .env.example .env

# Run
flask run --host=0.0.0.0 --port=8888
```

## License

This project is for personal use.
