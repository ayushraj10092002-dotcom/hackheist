import sqlite3
import tempfile
import unittest
from pathlib import Path

from werkzeug.security import generate_password_hash

from app import create_app


class HackHeistAppTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.sqlite3"
        self.app = create_app(
            {
                "TESTING": True,
                "DATABASE_PATH": str(self.db_path),
                "SECRET_KEY": "test-secret",
                "REGISTRATION_OPEN": True,
                "TEAM_SIZE_LIMIT": 2,
                "ADMIN_PASSWORD_HASH": generate_password_hash("admin-password"),
            }
        )
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp_dir.cleanup()

    def csrf(self):
        self.client.get("/admin/login")
        with self.client.session_transaction() as session:
            return session["_csrf_token"]

    def post(self, path, data):
        data = {**data, "_csrf_token": self.csrf()}
        return self.client.post(path, data=data, follow_redirects=False)

    def register(self, name, email):
        return self.post("/register", {"name": name, "email": email})

    def api_state(self, client=None):
        client = client or self.client
        response = client.get("/api/state")
        return response.get_json()

    def api_post(self, client, path, data):
        state = self.api_state(client)
        return client.post(
            path,
            json=data,
            headers={"X-CSRF-Token": state["csrf_token"]},
        )

    def test_registration_duplicate_and_persistence(self):
        self.assertEqual(self.register("Ada Lovelace", "Ada@Example.com").status_code, 302)
        duplicate = self.register("Another Name", "ada@example.com")
        self.assertEqual(duplicate.status_code, 302)

        db = sqlite3.connect(self.db_path)
        try:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM participants").fetchone()[0], 1)
        finally:
            db.close()
        restarted = create_app(
            {
                "TESTING": True,
                "DATABASE_PATH": str(self.db_path),
                "SECRET_KEY": "another-test-secret",
                "REGISTRATION_OPEN": True,
            }
        )
        self.assertEqual(restarted.test_client().get("/api/state").status_code, 200)
        db = sqlite3.connect(self.db_path)
        try:
            self.assertEqual(
                db.execute(
                    "SELECT name FROM participants WHERE email = ?",
                    ("ada@example.com",),
                ).fetchone()[0],
                "Ada Lovelace",
            )
        finally:
            db.close()

    def test_invalid_registration_is_rejected_without_persistence(self):
        response = self.api_post(self.client, "/api/register", {"name": "A", "email": "bad"})
        self.assertEqual(response.status_code, 422)
        db = sqlite3.connect(self.db_path)
        try:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM participants").fetchone()[0], 0)
        finally:
            db.close()

    def test_team_creation_joining_and_limit(self):
        self.assertEqual(
            self.api_post(
                self.client, "/api/register",
                {"name": "Ada Lovelace", "email": "ada@example.com"},
            ).status_code,
            201,
        )
        response = self.api_post(self.client, "/api/teams/create", {"team_name": "Kernel Crew"})
        self.assertEqual(response.status_code, 201)
        db = sqlite3.connect(self.db_path)
        try:
            code = db.execute("SELECT invite_code FROM teams").fetchone()[0]
        finally:
            db.close()

        member_client = self.app.test_client()
        self.assertEqual(
            self.api_post(
                member_client, "/api/register",
                {"name": "Grace Hopper", "email": "grace@example.com"},
            ).status_code,
            201,
        )
        self.assertEqual(
            self.api_post(member_client, "/api/teams/join", {"invite_code": code}).status_code,
            200,
        )
        full_client = self.app.test_client()
        self.assertEqual(
            self.api_post(
                full_client, "/api/register",
                {"name": "Linus Torvalds", "email": "linus@example.com"},
            ).status_code,
            201,
        )
        full = self.api_post(full_client, "/api/teams/join", {"invite_code": code})
        self.assertEqual(full.status_code, 409)
        self.assertIn("size limit", full.get_json()["error"])

    def test_team_actions_require_participant_session_and_reject_bad_code(self):
        unauthenticated = self.api_post(self.client, "/api/teams/create", {"team_name": "No Access"})
        self.assertEqual(unauthenticated.status_code, 401)
        self.assertEqual(
            self.api_post(
                self.client, "/api/register",
                {"name": "Ada Lovelace", "email": "ada@example.com"},
            ).status_code,
            201,
        )
        invalid = self.api_post(self.client, "/api/teams/join", {"invite_code": "INVALID"})
        self.assertEqual(invalid.status_code, 404)

    def test_state_changing_api_requests_require_csrf(self):
        response = self.client.post(
            "/api/register",
            json={"name": "Ada Lovelace", "email": "ada@example.com"},
        )
        self.assertEqual(response.status_code, 400)

    def test_registration_is_closed_by_default(self):
        closed_app = create_app(
            {
                "TESTING": True,
                "DATABASE_PATH": str(self.db_path) + "-closed",
                "SECRET_KEY": "test-secret",
                "REGISTRATION_OPEN": False,
            }
        )
        closed_client = closed_app.test_client()
        response = closed_client.post("/register", data={})
        self.assertEqual(response.status_code, 400)
        state = closed_client.get("/api/state")
        self.assertFalse(state.get_json()["registration_open"])
        self.assertEqual(
            closed_client.post(
                "/api/register",
                json={"name": "Ada Lovelace", "email": "ada@example.com"},
                headers={"X-CSRF-Token": state.get_json()["csrf_token"]},
            ).status_code,
            403,
        )

    def test_admin_requires_login_and_shows_records(self):
        self.assertEqual(self.client.get("/admin").status_code, 302)
        self.register("Ada Lovelace", "ada@example.com")
        login = self.post("/admin/login", {"password": "admin-password"})
        self.assertEqual(login.status_code, 302)
        dashboard = self.client.get("/admin")
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn(b"ada@example.com", dashboard.data)
        filtered = self.client.get("/admin?q=ada@example.com")
        self.assertEqual(filtered.status_code, 200)
        self.assertIn(b"ada@example.com", filtered.data)
        logout = self.post("/admin/logout", {})
        self.assertEqual(logout.status_code, 302)
        self.assertEqual(self.client.get("/admin").status_code, 302)


if __name__ == "__main__":
    unittest.main()
