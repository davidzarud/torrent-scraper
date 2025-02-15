from os import makedirs

from app.main import create_app
from app.services.config import *

app = create_app()

if __name__ == "__main__":
    makedirs(TMP_DIR, exist_ok=True)
    makedirs(SUBS_DIR, exist_ok=True)
    app.run(host="0.0.0.0", port=5000, debug=True)
