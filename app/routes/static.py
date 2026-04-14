from flask import Blueprint, send_from_directory

static_bp = Blueprint("static", __name__, url_prefix="")


# Serve the frontend
@static_bp.route("/")
def serve_frontend():
    return send_from_directory("static", "index.html")


# Catch-all route for Vue/React-style SPA routing
@static_bp.route("/<path:path>")
def catch_all(path):
    return send_from_directory("static", "index.html")
