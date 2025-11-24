from flask import Flask, jsonify
from threading import Thread
import os
import sys
from datetime import datetime
import pytz

app = Flask(__name__)

# Configure Flask for reliability
app.config['PROPAGATE_EXCEPTIONS'] = True
app.config['TRAP_HTTP_EXCEPTIONS'] = True

@app.route('/')
def home():
    """Primary health check endpoint for UptimeRobot"""
    try:
        return "Bot is alive! 🤖", 200
    except Exception as e:
        print(f"❌ Error in home endpoint: {e}", file=sys.stderr)
        return "error", 500

@app.route('/status')
def status():
    """Detailed status endpoint"""
    try:
        german_tz = pytz.timezone('Europe/Berlin')
        current_time = datetime.now(german_tz).strftime("%Y-%m-%d %H:%M:%S")
        
        return jsonify({
            "status": "running",
            "service": "YoYoXcloud Premium Inboxer Bot",
            "version": "1.0",
            "timestamp": current_time,
            "timezone": "Europe/Berlin (CET/CEST)"
        }), 200
    except Exception as e:
        print(f"❌ Error in status endpoint: {e}", file=sys.stderr)
        return jsonify({"status": "error"}), 500

@app.route('/ping')
def ping():
    """Simple ping endpoint"""
    try:
        return "pong", 200
    except Exception as e:
        print(f"❌ Error in ping endpoint: {e}", file=sys.stderr)
        return "error", 500

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors gracefully"""
    return jsonify({"message": "endpoint not found", "status": "ok"}), 200

@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors gracefully"""
    print(f"⚠️ Server error: {error}", file=sys.stderr)
    return jsonify({"message": "server error", "status": "error"}), 500

def run():
    """Run Flask server with error handling"""
    try:
        app.run(
            host='0.0.0.0', 
            port=5000,
            debug=False,
            use_reloader=False,
            threaded=True
        )
    except Exception as e:
        print(f"❌ Flask server error: {e}", file=sys.stderr)
        # Restart the server
        run()

def keep_alive():
    """Start keep-alive server in daemon thread"""
    try:
        t = Thread(target=run)
        t.daemon = True
        t.start()
        print("🌐 Keep-alive server started on port 5000")
    except Exception as e:
        print(f"❌ Failed to start keep-alive server: {e}", file=sys.stderr)
