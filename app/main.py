import logging
import os

from flask import Flask
from flask_cors import CORS

from app.routes import register_blueprints

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def create_app():
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    CORS(app)
    app.secret_key = os.urandom(24)

    # Register all blueprints
    register_blueprints(app)

    return app
