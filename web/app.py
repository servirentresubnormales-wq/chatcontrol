import os
import secrets
import hmac
import json
import logging
from datetime import datetime, timedelta
from functools import wraps

from flask import (Flask, render_template, request, redirect, url_for,
                   session, jsonify, abort)
from flask_cors import CORS

from models import init_db, Streamer, EventSettings, WebSession, OAuthState
from twitch_oauth import TwitchOAuth, generate_state

logger = logging.getLogger(__name__)

CSRF_TOKEN_KEY = "_csrf_token"
HEARTBEAT_TIMEOUT = int(os.environ.get("HEARTBEAT_TIMEOUT", "60"))


def generate_csrf_token() -> str:
    if CSRF_TOKEN_KEY not in session:
        session[CSRF_TOKEN_KEY] = secrets.token_hex(32)
    return session[CSRF_TOKEN_KEY]


def validate_csrf(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            token = request.headers.get("X-CSRF-Token") or (
                request.get_json(silent=True) or {}
            ).get("_csrf_token")
            if not token or not hmac.compare_digest(token, session.get(CSRF_TOKEN_KEY, "")):
                return jsonify({"error": "CSRF token missing or invalid"}), 403
        return f(*args, **kwargs)
    return decorated


def create_app(config: dict = None) -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    if os.environ.get("FLASK_ENV") == "production":
        app.config["SESSION_COOKIE_SECURE"] = True

    if config:
        app.config.update(config)

    allowed_origins = [
        o.strip()
        for o in os.environ.get("ALLOWED_ORIGINS", "").split(",")
        if o.strip()
    ]
    if not allowed_origins:
        allowed_origins = ["http://localhost:4321"]
    CORS(app, origins=allowed_origins, supports_credentials=True)

    app.jinja_env.globals["csrf_token"] = generate_csrf_token

    client_id = os.environ.get("TWITCH_CLIENT_ID", "")
    client_secret = os.environ.get("TWITCH_CLIENT_SECRET", "")
    redirect_uri = os.environ.get("TWITCH_REDIRECT_URI", "http://localhost:5000/auth/twitch/callback")

    app.twitch_oauth = TwitchOAuth(client_id, client_secret, redirect_uri)
    app.db_path = app.config.get("DB_PATH") or os.environ.get("DB_PATH") or os.path.join(os.path.dirname(__file__), "chatcontrol.db")
    app.frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:4321")
    init_db(app.db_path)

    register_routes(app)
    return app


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        session_id = session.get("session_id")
        if not session_id:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Not authenticated"}), 401
            return redirect(url_for("login"))

        ws = WebSession()
        sess = ws.get(session_id)
        if not sess:
            session.clear()
            if request.path.startswith("/api/"):
                return jsonify({"error": "Session expired"}), 401
            return redirect(url_for("login"))

        user = Streamer().get(sess["twitch_user_id"])
        if not user:
            session.clear()
            if request.path.startswith("/api/"):
                return jsonify({"error": "User not found"}), 401
            return redirect(url_for("login"))

        request.current_user = user
        return f(*args, **kwargs)
    return decorated


def register_routes(app: Flask):

    @app.route("/api/me")
    @login_required
    def api_me():
        user = request.current_user
        return jsonify({
            "twitch_user_id": user["twitch_user_id"],
            "twitch_login": user["twitch_login"],
            "display_name": user["display_name"],
            "minecraft_player": user["minecraft_player"],
            "enabled": bool(user["enabled"]),
            "bridge_connected": bool(user.get("bridge_connected", 0)),
            "minecraft_connected": bool(user.get("minecraft_connected", 0)),
        })

    @app.route("/api/settings", methods=["GET"])
    @login_required
    def api_get_settings():
        user = request.current_user
        events = EventSettings().get_all(user["twitch_user_id"])
        return jsonify({
            "minecraft_player": user["minecraft_player"],
            "enabled": bool(user["enabled"]),
            "events": events,
        })

    @app.route("/api/settings", methods=["PUT"])
    @login_required
    @validate_csrf
    def api_update_settings():
        user = request.current_user
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        streamer = Streamer()
        if "minecraft_player" in data:
            streamer.update_minecraft_player(user["twitch_user_id"], data["minecraft_player"])

        if "enabled" in data:
            streamer.update_enabled(user["twitch_user_id"], data["enabled"])

        if "events" in data:
            EventSettings().update_many(user["twitch_user_id"], data["events"])

        return jsonify({"success": True})

    @app.route("/api/events", methods=["GET"])
    @login_required
    def api_get_events():
        user = request.current_user
        events = EventSettings().get_all(user["twitch_user_id"])
        return jsonify(events)

    @app.route("/api/events/<int:event_number>", methods=["GET"])
    @login_required
    def api_get_event(event_number):
        user = request.current_user
        event = EventSettings().get(user["twitch_user_id"], event_number)
        if not event:
            return jsonify({"error": "Event not found"}), 404
        return jsonify(event)

    @app.route("/api/events/<int:event_number>", methods=["PUT"])
    @login_required
    @validate_csrf
    def api_update_event(event_number):
        user = request.current_user
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        success = EventSettings().update(user["twitch_user_id"], event_number, **data)
        if not success:
            return jsonify({"error": "Event not found or no changes"}), 404

        return jsonify({"success": True})

    @app.route("/api/events/batch", methods=["PUT"])
    @login_required
    @validate_csrf
    def api_update_events_batch():
        user = request.current_user
        data = request.get_json()
        if not data or "events" not in data:
            return jsonify({"error": "No events data provided"}), 400

        count = EventSettings().update_many(user["twitch_user_id"], data["events"])
        return jsonify({"success": True, "updated": count})

    @app.route("/api/csrf-token", methods=["GET"])
    @login_required
    def api_csrf_token():
        return jsonify({"csrf_token": generate_csrf_token()})

    @app.route("/auth/twitch")
    def auth_twitch():
        state = generate_state()
        oauth_state = OAuthState()
        oauth_state.create(state)
        session["oauth_state"] = state
        auth_url = app.twitch_oauth.get_authorization_url(state)
        return redirect(auth_url)

    @app.route("/auth/twitch/callback")
    def auth_twitch_callback():
        code = request.args.get("code")
        state = request.args.get("state")
        error = request.args.get("error")

        if error:
            logger.warning("Twitch OAuth error: %s", error)
            return redirect(f"{app.frontend_url}/login/?error=auth_denied")

        if not code or not state:
            abort(400)

        stored_state = session.get("oauth_state")
        if not stored_state or not hmac.compare_digest(state, stored_state):
            abort(403)

        oauth_state = OAuthState()
        if not oauth_state.use(state):
            abort(403)

        session.pop("oauth_state", None)

        token_data = app.twitch_oauth.exchange_code(code)
        if not token_data:
            logger.error("Failed to exchange authorization code")
            return redirect(f"{app.frontend_url}/login/?error=token_exchange_failed")

        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")

        validation = app.twitch_oauth.validate_token(access_token)
        if not validation:
            logger.error("Failed to validate access token")
            return redirect(f"{app.frontend_url}/login/?error=token_validation_failed")

        user_info = app.twitch_oauth.get_user_info(access_token)
        if not user_info:
            logger.error("Failed to get user info from Twitch")
            return redirect(f"{app.frontend_url}/login/?error=user_info_failed")

        streamer = Streamer()
        existing = streamer.get(user_info["user_id"])
        if existing:
            WebSession().delete_by_user(user_info["user_id"])

        user = streamer.get_or_create(
            twitch_user_id=user_info["user_id"],
            twitch_login=user_info["login"],
            display_name=user_info["display_name"],
            access_token=access_token,
            refresh_token=refresh_token,
        )

        session_id = secrets.token_urlsafe(32)
        expires_at = (datetime.utcnow() + timedelta(hours=24)).isoformat()
        ws = WebSession()
        ws.create(session_id, user["twitch_user_id"], expires_at)

        session.regenerate()
        session["session_id"] = session_id

        return redirect(f"{app.frontend_url}/dashboard/")

    @app.route("/api/logout", methods=["POST"])
    @login_required
    @validate_csrf
    def api_logout():
        session_id = session.get("session_id")
        if session_id:
            WebSession().delete(session_id)
        session.clear()
        return jsonify({"success": True})

    @app.route("/api/bridge/heartbeat", methods=["POST"])
    def api_bridge_heartbeat():
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        twitch_user_id = data.get("twitch_user_id")
        bridge_token = data.get("bridge_token")

        if not twitch_user_id or not bridge_token:
            return jsonify({"error": "Missing twitch_user_id or bridge_token"}), 400

        streamer = Streamer()
        if not streamer.authenticate_bridge(twitch_user_id, bridge_token):
            return jsonify({"error": "Invalid bridge credentials"}), 403

        streamer.update_heartbeat(twitch_user_id)
        return jsonify({"success": True})

    @app.route("/api/bridge/register", methods=["POST"])
    @login_required
    @validate_csrf
    def api_bridge_register():
        user = request.current_user
        streamer = Streamer()
        token = streamer.generate_bridge_token(user["twitch_user_id"])
        return jsonify({"bridge_token": token, "twitch_user_id": user["twitch_user_id"]})

    @app.route("/api/bridge/disconnect", methods=["POST"])
    @login_required
    @validate_csrf
    def api_bridge_disconnect():
        user = request.current_user
        Streamer().set_bridge_connected(user["twitch_user_id"], False)
        Streamer().set_minecraft_connected(user["twitch_user_id"], False)
        return jsonify({"success": True})

    @app.route("/api/heartbeat-check", methods=["POST"])
    def api_heartbeat_check():
        count = Streamer().check_heartbeat_timeout(HEARTBEAT_TIMEOUT)
        return jsonify({"timeout_disconnections": count})

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host="127.0.0.1", port=port, debug=debug)
