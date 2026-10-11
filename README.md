# HackHeist 2026 prototype

The existing five-section frontend remains available at `/`. When registration is enabled, the Event Details section loads registration and team controls from Flask. Registration is disabled by default, so the public page renders only “Registration Opening Soon” and submits no participant data.

## Local setup

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

Create a password hash:

```sh
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('change-this-password'))"
```

Copy `.env.example` to `.env` and provide `SECRET_KEY` and the generated `ADMIN_PASSWORD_HASH`. Export those values in the shell before starting Flask; this project does not load `.env` files automatically.

Run the development server:

```sh
export SECRET_KEY='local-only-random-secret'
export ADMIN_PASSWORD_HASH='paste-the-generated-hash'
export REGISTRATION_OPEN=false
python -m flask --app app run --debug
```

Visit `http://127.0.0.1:5000/`. The frontend continues to show “Registration Opening Soon” until organizers confirm the fields and rules. For controlled local testing only, enable the interface with `REGISTRATION_OPEN=true`:

```sh
export REGISTRATION_OPEN=true
export TEAM_SIZE_LIMIT=4
python -m flask --app app run --debug
```

The integrated browser flow uses these JSON endpoints:

- `GET /api/state`
- `POST /api/register`
- `POST /api/teams/create`
- `POST /api/teams/join`

Successful registration establishes a signed participant session. Team requests use that server-side session identity; they do not accept a participant ID or email from the browser. Each state-changing request sends the session CSRF token in the `X-CSRF-Token` header. The original form endpoints remain available for non-JavaScript testing:

- `POST /register`
- `POST /teams/create`
- `POST /teams/join`

Run the automated test-client flow with:

```sh
python -m unittest discover -s tests -v
```

The tests cover registration persistence, duplicate email handling, closed registration, participant authorization, team creation and joining, invalid invitation codes, team-size limits, CSRF handling, and admin authorization.

Do not set `REGISTRATION_OPEN=true` on a public deployment until organizers confirm the form fields and event rules.

The configurable team-size default is `4`; change `TEAM_SIZE_LIMIT` only after the organizers confirm the rule. The SQLite database is created at `instance/hackheist.sqlite3` by default and should not be committed or publicly served.

## Security notes

- SQL uses parameterized queries.
- Emails are normalized and unique case-insensitively.
- Registration and team actions validate data server-side.
- Admin passwords are checked against a Werkzeug password hash and never stored as plaintext.
- State-changing forms require a session-backed CSRF token.
- Admin records require an authenticated admin session.
- Set `SESSION_COOKIE_SECURE=true` when serving over HTTPS.
- Use a production WSGI server and a secret manager/environment variables for deployment.

## Render deployment preparation

`render.yaml` defines a Flask web service using Gunicorn:

```sh
gunicorn --bind 0.0.0.0:$PORT app:app
```

The service is intentionally configured with `REGISTRATION_OPEN=false`, `FLASK_DEBUG=false`, and secure session cookies. Set `ADMIN_PASSWORD_HASH` as a secret in Render; never put the hash in `render.yaml` or Git.

The default Render free service has ephemeral storage. Because this project uses SQLite, keep registration disabled there unless a persistent disk or an external production database is configured. The `/healthz` endpoint returns `{"status":"ok"}` for health checks.

To deploy after creating or authorizing a Render service:

1. Connect the GitHub repository to Render.
2. Select the `render.yaml` blueprint, or configure the same build and start commands.
3. Set `ADMIN_PASSWORD_HASH` in the Render environment.
4. Keep `REGISTRATION_OPEN=false` until the organizers approve the form and storage policy.
5. Verify `/healthz`, `/`, `/style.css`, `/script.js`, and all `/assets/...` URLs on the assigned public URL.

This audit prepared the Render configuration but did not create an account, deploy a service, or verify a public URL.

## GitHub submission

This project is ready to submit after reviewing the generated diff and confirming the organizer-provided event details. The root `.gitignore` excludes the virtual environment, SQLite database, Python caches, `.env`, and macOS metadata.

```sh
git init
git add .gitignore .env.example README.md requirements.txt render.yaml app.py index.html style.css script.js templates assets tests
git status --short
git commit -m "Prepare HackHeist event website submission"
git branch -M main
git remote add origin https://github.com/<your-account>/<your-repository>.git
git push -u origin main
```

Do not add `.env`, `instance/*.sqlite3`, or real administrator credentials to Git. Deployment has not been performed or verified by this audit.
