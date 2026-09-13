import pytest
from litestar.testing import TestClient

import one_line_day_py.src.app as app_module
from one_line_day_py.main import make_app
from one_line_day_py.src.data.sql_back import JournalSqlDb, UserSqlDb

ALICE = {"name": "Alice", "email": "alice@example.com", "password": "hunter22"}
BOB = {"name": "Bob", "email": "bob@example.com", "password": "correct-horse"}


@pytest.fixture
def app(tmp_path, monkeypatch):
    db_path = str(tmp_path / "test.db")
    monkeypatch.setattr(app_module.settings, "db_path", db_path)
    monkeypatch.setattr(app_module, "users_db", UserSqlDb(db_path))
    monkeypatch.setattr(app_module, "journals_db", JournalSqlDb(db_path))
    return make_app()


@pytest.fixture
def client(app):
    with TestClient(app=app) as c:
        yield c


class TestAuthController:
    def test_signup_creates_user_and_sets_session(self, client):
        response = client.post("/auth/signup", json=ALICE)

        assert response.status_code == 201
        body = response.json()
        assert body["name"] == ALICE["name"]
        assert body["email"] == ALICE["email"]
        assert "hashed_password" not in body
        assert "password" not in body

        assert client.get("/auth/me").status_code == 200

    def test_signup_with_duplicate_email_is_rejected(self, client):
        client.post("/auth/signup", json=ALICE)

        response = client.post(
            "/auth/signup",
            json={
                "name": "Someone Else",
                "email": ALICE["email"],
                "password": "whatever",
            },
        )

        assert response.status_code == 409

    def test_login_with_correct_credentials_succeeds(self, client):
        client.post("/auth/signup", json=ALICE)
        client.post("/auth/logout")

        response = client.post(
            "/auth/login", json={"email": ALICE["email"], "password": ALICE["password"]}
        )

        assert response.status_code == 201
        assert client.get("/auth/me").status_code == 200

    def test_login_with_wrong_password_is_rejected(self, client):
        client.post("/auth/signup", json=ALICE)
        client.post("/auth/logout")

        response = client.post(
            "/auth/login", json={"email": ALICE["email"], "password": "wrong-password"}
        )

        assert response.status_code == 401

    def test_login_with_unknown_email_is_rejected(self, client):
        response = client.post(
            "/auth/login", json={"email": "nobody@example.com", "password": "whatever"}
        )

        assert response.status_code == 401

    def test_me_requires_authentication(self, client):
        assert client.get("/auth/me").status_code == 401

    def test_logout_invalidates_session(self, client):
        client.post("/auth/signup", json=ALICE)
        assert client.get("/auth/me").status_code == 200

        client.post("/auth/logout")

        assert client.get("/auth/me").status_code == 401


class TestJournalControllerAuthorization:
    def test_journal_routes_require_authentication(self, client):
        assert client.get("/journals/").status_code == 401

    def test_users_only_see_their_own_entries(self, app):
        with TestClient(app=app) as alice, TestClient(app=app) as bob:
            alice.post("/auth/signup", json=ALICE)
            bob.post("/auth/signup", json=BOB)

            create_response = alice.post("/journals/?date=2026-01-01&message=hi")
            assert create_response.status_code == 201
            entry_id = create_response.json()["id"]

            assert bob.get("/journals/").json() == []
            assert bob.get(f"/journals/{entry_id}").status_code == 404
            assert bob.get(f"/journals/{entry_id}/author").status_code == 404
            assert bob.put(f"/journals/{entry_id}?message=hijacked").status_code == 404
            assert bob.delete(f"/journals/{entry_id}").status_code == 404

            assert alice.get(f"/journals/{entry_id}").status_code == 200
