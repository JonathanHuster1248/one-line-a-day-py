class TestRootController:
    def test_root_redirects_to_swagger_docs(self, client):
        response = client.get("/", follow_redirects=False)

        assert response.status_code in (301, 302, 307, 308)
        assert response.headers["location"] == "/schema/swagger/"

    def test_root_redirect_requires_no_authentication(self, client):
        response = client.get("/", follow_redirects=False)

        assert response.status_code != 401

    def test_favicon_is_served(self, client):
        response = client.get("/favicon.ico")

        assert response.status_code == 200

    def test_ping_returns_ok(self, client):
        response = client.get("/ping")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_ping_requires_no_authentication(self, client):
        response = client.get("/ping")

        assert response.status_code != 401


class TestDocsDisabled:
    def test_schema_and_root_are_not_served_when_docs_disabled(
        self, tmp_path, monkeypatch
    ):
        from litestar.testing import TestClient

        from one_line_day_py.main import make_app
        from one_line_day_py.src.settings import settings

        monkeypatch.setattr(settings, "db_path", tmp_path / "test.db")
        monkeypatch.setattr(settings, "enable_docs", False)

        with TestClient(app=make_app()) as c:
            assert c.get("/schema/swagger/").status_code == 404
            assert c.get("/schema/openapi.json").status_code == 404
            assert c.get("/", follow_redirects=False).status_code == 404
            assert c.get("/ping").status_code == 200
