import os
import time
import logging
from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from threading import Thread

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Setup database base class
class Base(DeclarativeBase):
    pass

# Setup database with SQLAlchemy
db = SQLAlchemy(model_class=Base)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Configure database URL
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL") or "sqlite:///site.db"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the database with the app
db.init_app(app)

# Fix for proxied requests in Replit
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure CORS to allow embedding
@app.after_request
def add_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    if response.mimetype == "text/html":
        response.headers["Content-Security-Policy"] = "default-src * 'unsafe-inline' 'unsafe-eval'; img-src * data:"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "ALLOWALL"
    response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"
    return response

# Initialize database tables
with app.app_context():
    import models  # Ensure your models are imported for database creation
    db.create_all()

@app.route('/')
def home():
    """Home page route that displays bot status and information."""
    logger.debug(f"Serving home page, request path: {request.path}")
    client_id = os.environ.get('DISCORD_CLIENT_ID', '')
    return render_template('home.html', client_id=client_id)

@app.route('/status')
def status():
    """Returns the current status of the bot."""
    return jsonify({"status": "online", "message": "ServerSetup Bot is running!"})

@app.route('/keep-alive')
def keep_alive():
    """Endpoint for UptimeRobot to ping to keep the bot alive."""
    logger.debug(f"Keep-alive pinged, request path: {request.path}")
    return jsonify({"status": "alive", "bot": "ServerSetup Bot", "uptime": "active", "timestamp": time.time()})

# Function to run the Discord bot
def run_discord_bot():
    from bot import start_bot  # Adjust according to your bot's structure
    start_bot()

if __name__ == '__main__':
    # Start the Discord bot in a separate thread
    bot_thread = Thread(target=run_discord_bot)
    bot_thread.start()

    # Start the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)import os
import time
import logging
from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Setup database base class
class Base(DeclarativeBase):
    pass

# Setup database with SQLAlchemy
db = SQLAlchemy(model_class=Base)

# Create the Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Configure database URL
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL") or "sqlite:///site.db"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the database with the app
db.init_app(app)

# Fix for proxied requests in Replit
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure CORS to allow embedding
@app.after_request
def add_headers(response):
    # Ensure CORS is allowed
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"

    # Only add CSP to HTML responses
    if response.mimetype == "text/html":
        response.headers["Content-Security-Policy"] = "default-src * 'unsafe-inline' 'unsafe-eval'; img-src * data:"

    response.headers["X-Content-Type-Options"] = "nosniff"

    # Add specific headers for proxy compatibility
    response.headers["X-Frame-Options"] = "ALLOWALL"
    response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"

    return response

# Initialize database tables
with app.app_context():
    # Import models to ensure they're registered with SQLAlchemy
    import models
    db.create_all()

# We'll start the bot only once at the end, not here

@app.route('/')
def home():
    """Home page route that displays bot status and information."""
    logger.debug(f"Serving home page, request path: {request.path}")
    # Get bot client ID from environment or use a default
    client_id = os.environ.get('DISCORD_CLIENT_ID', '')
    return render_template('home.html', client_id=client_id)

@app.route('/status')
def status():
    """Returns the current status of the bot."""
    try:
        client_id = os.environ.get('DISCORD_CLIENT_ID', '')
        return jsonify({
            "status": "online",
            "message": "ServerSetup Bot is running!",
            "client_id": client_id,
            "timestamp": time.time()
        })
    except Exception as e:
        logger.error(f"Error in status endpoint: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/keep-alive')
def keep_alive():
    """Endpoint for UptimeRobot to ping to keep the bot alive."""
    logger.debug(f"Keep-alive pinged, request path: {request.path}")
    return jsonify({
        "status": "alive", 
        "bot": "ServerSetup Bot", 
        "uptime": "active", 
        "timestamp": time.time()
    })

# For better logging of uptime monitoring
uptime_counter = 0

@app.route('/uptime')
def uptime():
    """More detailed uptime monitoring endpoint with counter."""
    global uptime_counter
    uptime_counter += 1

    logger.debug(f"Uptime check #{uptime_counter}, request path: {request.path}")

    # Get bot client ID to confirm bot is running
    client_id = os.environ.get('DISCORD_CLIENT_ID', '')
    bot_connected = bool(client_id)

    return jsonify({
        "status": "online",
        "counter": uptime_counter,
        "bot_connected": bot_connected,
        "timestamp": time.time(),
        "message": f"Bot has been pinged {uptime_counter} times"
    })

@app.route('/favicon.ico')
def favicon():
    """Serve favicon to avoid 404 errors."""
    return app.send_static_file('img/favicon.ico')



# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    logger.error(f"404 error: {e}, path: {request.path}")
    client_id = os.environ.get('DISCORD_CLIENT_ID', '')
    return render_template('home.html', error="Page not found", client_id=client_id), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"500 error: {e}")
    client_id = os.environ.get('DISCORD_CLIENT_ID', '')
    return render_template('home.html', error="Internal server error", client_id=client_id), 500

# Start Discord bot only once when running as main
bot_thread = None

if __name__ == '__main__':
    # Import and start the bot
    from bot import start_bot
    bot_thread = start_bot()

    # Start the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)