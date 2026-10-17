class TestAuthController:
    def test_signup_creates_user_and_sets_session(self, client, alice):
        response = client.post("/auth/signup", json=alice)

        assert response.status_code == 201
        body = response.json()
        assert body["name"] == alice["name"]
        assert body["email"] == alice["email"]
        assert "hashed_password" not in body
        assert "password" not in body

        assert client.get("/auth/me").status_code == 200

    def test_signup_with_duplicate_email_is_rejected(self, client, alice):
        client.post("/auth/signup", json=alice)

        response = client.post(
            "/auth/signup",
            json={
                "name": "Someone Else",
                "email": alice["email"],
                "password": "whatever",
            },
        )

        assert response.status_code == 409

    def test_login_with_correct_credentials_succeeds(self, client, alice):
        client.post("/auth/signup", json=alice)
        client.post("/auth/logout")

        response = client.post(
            "/auth/login",
            json={"email": alice["email"], "password": alice["password"]},
        )

        assert response.status_code == 201
        assert client.get("/auth/me").status_code == 200

    def test_login_with_wrong_password_is_rejected(self, client, alice):
        client.post("/auth/signup", json=alice)
        client.post("/auth/logout")

        response = client.post(
            "/auth/login", json={"email": alice["email"], "password": "wrong-password"}
        )

        assert response.status_code == 401

    def test_login_with_unknown_email_is_rejected(self, client):
        response = client.post(
            "/auth/login", json={"email": "nobody@example.com", "password": "whatever"}
        )

        assert response.status_code == 401

    def test_me_requires_authentication(self, client):
        assert client.get("/auth/me").status_code == 401

    def test_logout_invalidates_session(self, client, alice):
        client.post("/auth/signup", json=alice)
        assert client.get("/auth/me").status_code == 200

        client.post("/auth/logout")

        assert client.get("/auth/me").status_code == 401
