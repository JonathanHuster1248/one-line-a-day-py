from uuid import uuid4

from litestar.testing import TestClient


class TestUserController:
    def test_list_users_requires_authentication(self, client):
        assert client.get("/users/").status_code == 401

    def test_get_user_by_id_requires_authentication(self, client):
        assert client.get(f"/users/{uuid4()}").status_code == 401

    def test_update_user_requires_authentication(self, client):
        assert client.put(f"/users/{uuid4()}").status_code == 401

    def test_delete_user_requires_authentication(self, client):
        assert client.delete(f"/users/{uuid4()}").status_code == 401

    def test_list_users_returns_signed_up_users(self, client, alice, bob):
        client.post("/auth/signup", json=alice)
        client.post("/auth/signup", json=bob)

        response = client.get("/users/")

        assert response.status_code == 200
        names = {user["name"] for user in response.json()}
        assert names == {alice["name"], bob["name"]}

    def test_list_users_never_leaks_hashed_password(self, client, alice):
        client.post("/auth/signup", json=alice)

        response = client.get("/users/")

        assert all("hashed_password" not in user for user in response.json())

    def test_get_user_by_id_returns_matching_user(self, client, alice):
        signup_response = client.post("/auth/signup", json=alice)
        user_id = signup_response.json()["id"]

        response = client.get(f"/users/{user_id}")

        assert response.status_code == 200
        assert response.json() == signup_response.json()

    def test_get_user_by_id_unknown_id_errors(self, client, alice):
        client.post("/auth/signup", json=alice)

        response = client.get(f"/users/{uuid4()}")

        assert response.status_code == 404

    def test_get_user_by_name_returns_matching_user(self, client, alice):
        signup_response = client.post("/auth/signup", json=alice)

        response = client.get(f"/users/name/{alice['name']}")

        assert response.status_code == 200
        assert response.json() == signup_response.json()

    def test_get_user_by_name_unknown_name_errors(self, client, alice):
        client.post("/auth/signup", json=alice)

        response = client.get("/users/name/NoSuchUser")

        assert response.status_code == 404

    def test_update_user_changes_name(self, client, alice):
        signup_response = client.post("/auth/signup", json=alice)
        user_id = signup_response.json()["id"]

        response = client.put(f"/users/{user_id}", params={"name": "New Name"})

        assert response.status_code == 200
        assert response.json()["name"] == "New Name"
        assert response.json()["id"] == user_id

    def test_update_user_without_fields_is_rejected(self, client, alice):
        signup_response = client.post("/auth/signup", json=alice)
        user_id = signup_response.json()["id"]

        response = client.put(f"/users/{user_id}")

        assert response.status_code == 400

    def test_update_user_unknown_id_is_forbidden(self, client, alice):
        # The target id belongs to no one, including the caller, so the
        # ownership check rejects it before a lookup ever happens.
        client.post("/auth/signup", json=alice)

        response = client.put(f"/users/{uuid4()}", params={"name": "New Name"})

        assert response.status_code == 403

    def test_delete_user_removes_user(self, app, alice, bob):
        with TestClient(app=app) as alice_client, TestClient(app=app) as bob_client:
            alice_client.post("/auth/signup", json=alice)
            alice_id = alice_client.get("/auth/me").json()["id"]
            bob_client.post("/auth/signup", json=bob)

            response = alice_client.delete(f"/users/{alice_id}")

            assert response.status_code == 204
            names = {user["name"] for user in bob_client.get("/users/").json()}
            assert names == {bob["name"]}

    def test_delete_user_unknown_id_is_forbidden(self, client, alice):
        # The target id belongs to no one, including the caller, so the
        # ownership check rejects it before a lookup ever happens.
        client.post("/auth/signup", json=alice)

        response = client.delete(f"/users/{uuid4()}")

        assert response.status_code == 403

    def test_update_user_as_non_owner_is_forbidden(self, app, alice, bob):
        with TestClient(app=app) as alice_client, TestClient(app=app) as bob_client:
            alice_id = alice_client.post("/auth/signup", json=alice).json()["id"]
            bob_client.post("/auth/signup", json=bob)

            response = bob_client.put(
                f"/users/{alice_id}", params={"name": "Hijacked"}
            )

            assert response.status_code == 403
            assert alice_client.get(f"/users/{alice_id}").json()["name"] == alice["name"]

    def test_delete_user_as_non_owner_is_forbidden(self, app, alice, bob):
        with TestClient(app=app) as alice_client, TestClient(app=app) as bob_client:
            alice_id = alice_client.post("/auth/signup", json=alice).json()["id"]
            bob_client.post("/auth/signup", json=bob)

            response = bob_client.delete(f"/users/{alice_id}")

            assert response.status_code == 403
            assert alice_client.get(f"/users/{alice_id}").status_code == 200
