from .favorites import favorites_bp
from .movies import movies_bp
from .static import static_bp
from .stream import stream_bp
from .subtitles import subtitles_bp
from .torrents import torrents_bp
from .tv_shows import tv_shows_bp

# List of all blueprints
blueprints = [favorites_bp, movies_bp, static_bp, stream_bp, subtitles_bp, torrents_bp, tv_shows_bp]


def register_blueprints(app):
    for bp in blueprints:
        app.register_blueprint(bp, url_prefix=bp.url_prefix)
