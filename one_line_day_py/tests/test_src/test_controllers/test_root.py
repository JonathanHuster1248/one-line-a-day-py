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
