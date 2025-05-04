import os
import time
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
# Main app already handles web functionality

class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
# create the app
app = Flask(__name__)
# setup a secret key, required by sessions
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "a secret key"
# configure the database, relative to the app instance folder
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL") or "sqlite:///site.db"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
# initialize the app with the extension, flask-sqlalchemy >= 3.0.x
db.init_app(app)

# Import handlers from app.py
from app import add_headers, home, status, keep_alive, uptime, favicon, page_not_found, server_error

# Register route handlers
app.after_request(add_headers)
app.route("/")(home)
app.route("/status")(status)

@app.route("/ping")
def ping():
    """Quick ping endpoint for UptimeBot."""
    return "pong"

@app.route("/health")
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "uptime": time.time() - app.start_time,
        "memory_usage": os.popen('ps -o rss= -p %d' % os.getpid()).read().strip()
    })

app.route("/favicon.ico")(favicon)
app.errorhandler(404)(page_not_found)
app.errorhandler(500)(server_error)

# Store app start time
app.start_time = time.time()

with app.app_context():
    # Import models to ensure they're registered with SQLAlchemy
    import models  # noqa: F401

    # Create all tables
    db.create_all()

    # Start the Discord bot
    from bot import start_bot
    start_bot()

from app import app

if __name__ == "__main__":
    # Start the Flask app
    app.run(host='0.0.0.0', port=5000)