import os
import time
import logging
from flask import Flask, jsonify, request, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from threading import Thread

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# SQLAlchemy base
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_secret_key")

# Database config
database_url = os.environ.get("DATABASE_URL")
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

try:
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url or "sqlite:///site.db"
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
except:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///site.db"

db.init_app(app)

# Proxy fix for Replit or Render
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# CORS headers
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

# Initialize DB tables
with app.app_context():
    import models
    db.create_all()

@app.route('/')
def home():
    client_id = os.environ.get('DISCORD_CLIENT_ID', '')
    return render_template('home.html', client_id=client_id)

@app.route('/status')
def status():
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
    logger.debug("Keep-alive pinged")
    return jsonify({
        "status": "alive",
        "bot": "ServerSetup Bot",
        "uptime": "active",
        "timestamp": time.time()
    })

uptime_counter = 0

@app.route('/uptime')
def uptime():
    global uptime_counter
    uptime_counter += 1
    client_id = os.environ.get('DISCORD_CLIENT_ID', '')
    return jsonify({
        "status": "online",
        "counter": uptime_counter,
        "bot_connected": bool(client_id),
        "timestamp": time.time(),
        "message": f"Bot has been pinged {uptime_counter} times"
    })

@app.route('/favicon.ico')
def favicon():
    return app.send_static_file('img/favicon.ico')

@app.route('/terms')
def terms():
    client_id = os.environ.get('DISCORD_CLIENT_ID', '')
    return render_template('terms.html', client_id=client_id)

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

# Start Discord bot in a thread
def run_discord_bot():
    from bot import start_bot
    start_bot()

if __name__ == '__main__':
    bot_thread = Thread(target=run_discord_bot)
    bot_thread.start()
    app.run(host='0.0.0.0', port=5000, debug=True)