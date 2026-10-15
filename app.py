import os
import re
import secrets
import sqlite3
from datetime import timedelta
from contextlib import contextmanager
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    abort,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.security import check_password_hash


BASE_DIR = Path(__file__).resolve().parent
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
DEFAULT_DATABASE = (
    Path("/tmp") / "hackheist.sqlite3"
    if os.environ.get("VERCEL")
    else BASE_DIR / "instance" / "hackheist.sqlite3"
)


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        DATABASE_PATH=os.environ.get("DATABASE_PATH", str(DEFAULT_DATABASE)),
        REGISTRATION_OPEN=os.environ.get("REGISTRATION_OPEN", "true").lower() == "true",
        TEAM_SIZE_LIMIT=int(os.environ.get("TEAM_SIZE_LIMIT", "4")),
        GOOGLE_FORM_URL=os.environ.get(
            "GOOGLE_FORM_URL",
            "https://docs.google.com/forms/d/e/1FAIpQLSfVNx0ANEqMHLlsm-qei1T_ARVQa9C97G1bzYVMt-OGNvQSBg/viewform?usp=publish-edito",
        ),
        ADMIN_PASSWORD_HASH=os.environ.get("ADMIN_PASSWORD_HASH", ""),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=8),
    )
    if test_config:
        app.config.update(test_config)

    if app.config["TEAM_SIZE_LIMIT"] < 1:
        raise ValueError("TEAM_SIZE_LIMIT must be at least 1")

    Path(app.config["DATABASE_PATH"]).parent.mkdir(parents=True, exist_ok=True)
    init_db(app)

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response

    @app.context_processor
    def inject_csrf_token():
        return {"csrf_token": csrf_token}

    @app.get("/")
    def index():
        return send_from_directory(BASE_DIR, "index.html")

    @app.get("/style.css")
    def stylesheet():
        return send_from_directory(BASE_DIR, "style.css")

    @app.get("/script.js")
    def javascript():
        response = send_from_directory(BASE_DIR, "script.js")
        response.cache_control.no_cache = True
        response.cache_control.must_revalidate = True
        return response

    @app.get("/assets/<path:filename>")
    def assets(filename):
        return send_from_directory(BASE_DIR / "assets", filename)

    @app.get("/healthz")
    def healthz():
        return jsonify({"status": "ok"})

    @app.get("/api/state")
    def api_state():
        return jsonify(
            {
                "registration_open": app.config["REGISTRATION_OPEN"],
                "csrf_token": csrf_token(),
                "participant": current_participant(app),
                "team_size_limit": app.config["TEAM_SIZE_LIMIT"],
                "google_form_url": app.config["GOOGLE_FORM_URL"],
            }
        )

    @app.post("/api/register")
    def api_register():
        require_csrf()
        if not app.config["REGISTRATION_OPEN"]:
            return jsonify({"error": "Registration is opening soon."}), 403
        payload = request.get_json(silent=True) or request.form
        name = clean_text(payload.get("name"), 100)
        email = clean_email(payload.get("email"))
        if not name or len(name) < 2:
            return jsonify({"error": "Enter a valid name."}), 422
        if not email:
            return jsonify({"error": "Enter a valid email address."}), 422
        try:
            with get_db(app) as db:
                cursor = db.execute(
                    "INSERT INTO participants (name, email) VALUES (?, ?)",
                    (name, email),
                )
                participant_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            return jsonify({"error": "That email is already registered."}), 409
        session["participant_id"] = participant_id
        return jsonify(
            {"message": "Registration received. Team features are now unlocked."}
        ), 201

    @app.post("/api/teams/create")
    def api_create_team():
        require_csrf()
        if not app.config["REGISTRATION_OPEN"]:
            return jsonify({"error": "Registration is opening soon."}), 403
        participant = current_participant(app)
        if participant is None:
            return jsonify({"error": "Register before creating a team."}), 401
        payload = request.get_json(silent=True) or request.form
        team_name = clean_text(payload.get("team_name"), 80)
        if not team_name or len(team_name) < 2:
            return jsonify({"error": "Enter a valid team name."}), 422
        with get_db(app) as db:
            invite_code = new_invite_code(db)
            try:
                cursor = db.execute(
                    "INSERT INTO teams (name, invite_code) VALUES (?, ?)",
                    (team_name, invite_code),
                )
                db.execute(
                    "INSERT INTO team_members (team_id, participant_id, is_leader) "
                    "VALUES (?, ?, 1)",
                    (cursor.lastrowid, participant["id"]),
                )
            except sqlite3.IntegrityError:
                return jsonify({"error": "That team name is already in use."}), 409
        return jsonify({"message": f"Team created. Invitation code: {invite_code}."}), 201

    @app.post("/api/teams/join")
    def api_join_team():
        require_csrf()
        if not app.config["REGISTRATION_OPEN"]:
            return jsonify({"error": "Registration is opening soon."}), 403
        participant = current_participant(app)
        if participant is None:
            return jsonify({"error": "Register before joining a team."}), 401
        payload = request.get_json(silent=True) or request.form
        invite_code = clean_text(payload.get("invite_code"), 12).upper()
        if not invite_code:
            return jsonify({"error": "Enter an invitation code."}), 422
        with get_db(app) as db:
            team = db.execute(
                "SELECT id, name FROM teams WHERE invite_code = ?", (invite_code,)
            ).fetchone()
            if team is None:
                return jsonify({"error": "That invitation code is not valid."}), 404
            member_count = db.execute(
                "SELECT COUNT(*) AS count FROM team_members WHERE team_id = ?",
                (team["id"],),
            ).fetchone()["count"]
            if member_count >= app.config["TEAM_SIZE_LIMIT"]:
                return jsonify({"error": "That team has reached its size limit."}), 409
            try:
                db.execute(
                    "INSERT INTO team_members (team_id, participant_id) VALUES (?, ?)",
                    (team["id"], participant["id"]),
                )
            except sqlite3.IntegrityError:
                return jsonify({"error": "You are already on that team."}), 409
        return jsonify({"message": f"You joined {team['name']}."})

    @app.post("/register")
    def register():
        require_csrf()
        if not app.config["REGISTRATION_OPEN"]:
            abort(403, description="Registration is not open yet.")

        name = clean_text(request.form.get("name"), 100)
        email = clean_email(request.form.get("email"))
        if not name or len(name) < 2:
            return form_error("Enter a valid name.", "register")
        if not email:
            return form_error("Enter a valid email address.", "register")

        try:
            with get_db(app) as db:
                cursor = db.execute(
                    "INSERT INTO participants (name, email) VALUES (?, ?)",
                    (name, email),
                )
                participant_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            return form_error("That email is already registered.", "register")

        # Save the new participant in the session so team actions know who is logged in.
        session["participant_id"] = participant_id
        flash("Registration received. Keep your invitation code safe.", "success")
        return redirect(url_for("index", _anchor="details"))

    @app.post("/teams/create")
    def create_team():
        require_csrf()
        if not app.config["REGISTRATION_OPEN"]:
            abort(403, description="Registration is not open yet.")

        team_name = clean_text(request.form.get("team_name"), 80)
        if not team_name or len(team_name) < 2:
            return form_error("Enter a valid team name.", "team")
        participant = current_participant(app)
        if participant is None:
            return form_error("Register before creating a team.", "team")

        with get_db(app) as db:
            invite_code = new_invite_code(db)
            try:
                cursor = db.execute(
                    "INSERT INTO teams (name, invite_code) VALUES (?, ?)",
                    (team_name, invite_code),
                )
                db.execute(
                    "INSERT INTO team_members (team_id, participant_id, is_leader) "
                    "VALUES (?, ?, 1)",
                    (cursor.lastrowid, participant["id"]),
                )
            except sqlite3.IntegrityError:
                return form_error("That team name is already in use.", "team")

        flash(f"Team created. Invitation code: {invite_code}", "success")
        return redirect(url_for("index", _anchor="details"))

    @app.post("/teams/join")
    def join_team():
        require_csrf()
        if not app.config["REGISTRATION_OPEN"]:
            abort(403, description="Registration is not open yet.")

        invite_code = clean_text(request.form.get("invite_code"), 12).upper()
        participant = current_participant(app)
        if participant is None:
            return form_error("Register before joining a team.", "team")
        if not invite_code:
            return form_error("Enter an invitation code.", "team")

        with get_db(app) as db:
            team = db.execute(
                "SELECT id, name FROM teams WHERE invite_code = ?", (invite_code,)
            ).fetchone()
            if team is None:
                return form_error("Check your registered email and invitation code.", "team")

            member_count = db.execute(
                "SELECT COUNT(*) AS count FROM team_members WHERE team_id = ?",
                (team["id"],),
            ).fetchone()["count"]
            if member_count >= app.config["TEAM_SIZE_LIMIT"]:
                return form_error("That team has reached its configured size limit.", "team")

            try:
                db.execute(
                    "INSERT INTO team_members (team_id, participant_id) VALUES (?, ?)",
                    (team["id"], participant["id"]),
                )
            except sqlite3.IntegrityError:
                return form_error("You are already on that team.", "team")

        flash(f"You joined {team['name']}.", "success")
        return redirect(url_for("index", _anchor="details"))

    @app.get("/admin/login")
    def admin_login():
        return render_template("admin_login.html")

    @app.post("/admin/login")
    def admin_login_submit():
        require_csrf()
        password = request.form.get("password", "")
        password_hash = app.config["ADMIN_PASSWORD_HASH"]
        if not password_hash or not check_password_hash(password_hash, password):
            flash("Invalid admin credentials.", "error")
            return redirect(url_for("admin_login"))
        session.clear()
        session["admin_authenticated"] = True
        session.permanent = True
        return redirect(url_for("admin_dashboard"))

    @app.post("/admin/logout")
    @admin_required
    def admin_logout():
        require_csrf()
        session.clear()
        return redirect(url_for("admin_login"))

    @app.get("/admin")
    @admin_required
    def admin_dashboard():
        query = clean_text(request.args.get("q"), 100)
        pattern = f"%{query}%"
        with get_db(app) as db:
            participants = db.execute(
                """
                SELECT id, name, email, created_at
                FROM participants
                WHERE ? = '' OR name LIKE ? OR email LIKE ?
                ORDER BY created_at DESC
                """,
                (query, pattern, pattern),
            ).fetchall()
            teams = db.execute(
                """
                SELECT teams.id, teams.name, teams.invite_code, teams.created_at,
                       COUNT(team_members.id) AS member_count
                FROM teams
                LEFT JOIN team_members ON team_members.team_id = teams.id
                WHERE ? = '' OR teams.name LIKE ? OR teams.invite_code LIKE ?
                GROUP BY teams.id
                ORDER BY teams.created_at DESC
                """,
                (query, pattern, pattern),
            ).fetchall()
            participant_count = db.execute(
                "SELECT COUNT(*) AS count FROM participants"
            ).fetchone()["count"]
            team_count = db.execute("SELECT COUNT(*) AS count FROM teams").fetchone()["count"]
        return render_template(
            "admin_dashboard.html",
            participants=participants,
            teams=teams,
            participant_count=participant_count,
            team_count=team_count,
            query=query,
            team_size_limit=app.config["TEAM_SIZE_LIMIT"],
        )

    return app


def init_db(app):
    with get_db(app) as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                invite_code TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS team_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
                participant_id INTEGER NOT NULL REFERENCES participants(id) ON DELETE CASCADE,
                is_leader INTEGER NOT NULL DEFAULT 0,
                UNIQUE(team_id, participant_id)
            );
            """
        )


@contextmanager
def get_db(app):
    connection = sqlite3.connect(app.config["DATABASE_PATH"])
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def csrf_token():
    token = session.get("_csrf_token")
    if token is None:
        token = secrets.token_urlsafe(32)
        session["_csrf_token"] = token
    return token


def require_csrf():
    submitted = request.form.get("_csrf_token", "") or request.headers.get("X-CSRF-Token", "")
    expected = session.get("_csrf_token", "")
    if not submitted or not expected or not secrets.compare_digest(submitted, expected):
        abort(400, description="Invalid CSRF token.")


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_authenticated"):
            return redirect(url_for("admin_login"))
        return view(*args, **kwargs)

    return wrapped


def clean_text(value, maximum):
    if not isinstance(value, str):
        return ""
    return " ".join(value.split())[:maximum]


def clean_email(value):
    email = clean_text(value, 254).lower()
    return email if EMAIL_RE.fullmatch(email) else ""


def current_participant(app):
    participant_id = session.get("participant_id")
    if not participant_id:
        return None
    with get_db(app) as db:
        participant = db.execute(
            "SELECT id, name, email FROM participants WHERE id = ?",
            (participant_id,),
        ).fetchone()
    if participant is None:
        session.pop("participant_id", None)
        return None
    return dict(participant)


def new_invite_code(db):
    for _ in range(10):
        code = secrets.token_urlsafe(6).replace("-", "").replace("_", "").upper()[:8]
        if not db.execute("SELECT 1 FROM teams WHERE invite_code = ?", (code,)).fetchone():
            return code
    raise RuntimeError("Could not generate a unique invitation code.")


def form_error(message, form_name):
    flash(message, "error")
    return redirect(url_for("index", _anchor=form_name))


app = create_app()


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true")
