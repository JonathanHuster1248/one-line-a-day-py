from litestar.testing import TestClient


class TestJournalController:
    def test_journal_routes_require_authentication(self, client):
        assert client.get("/journals/").status_code == 401

    def test_users_only_see_their_own_entries(self, app, alice, bob):
        with TestClient(app=app) as alice_client, TestClient(app=app) as bob_client:
            alice_client.post("/auth/signup", json=alice)
            bob_client.post("/auth/signup", json=bob)

            create_response = alice_client.post("/journals/?date=2026-01-01&message=hi")
            assert create_response.status_code == 201
            entry_id = create_response.json()["id"]

            assert bob_client.get("/journals/").json() == []
            assert bob_client.get(f"/journals/{entry_id}").status_code == 404
            assert bob_client.get(f"/journals/{entry_id}/author").status_code == 404
            assert (
                bob_client.put(f"/journals/{entry_id}?message=hijacked").status_code
                == 404
            )
            assert bob_client.delete(f"/journals/{entry_id}").status_code == 404

            assert alice_client.get(f"/journals/{entry_id}").status_code == 200

    def test_owner_can_get_entry_author(self, client, alice):
        client.post("/auth/signup", json=alice)
        create_response = client.post("/journals/?date=2026-01-01&message=hi")
        entry_id = create_response.json()["id"]

        response = client.get(f"/journals/{entry_id}/author")

        assert response.status_code == 200
        assert response.json() == create_response.json()["author_id"]

    def test_owner_can_update_entry(self, client, alice):
        client.post("/auth/signup", json=alice)
        create_response = client.post("/journals/?date=2026-01-01&message=hi")
        entry_id = create_response.json()["id"]

        response = client.put(f"/journals/{entry_id}?message=updated")

        assert response.status_code == 200
        assert response.json()["message"] == "updated"
        assert response.json()["date"] == "2026-01-01"

    def test_owner_can_delete_entry(self, client, alice):
        client.post("/auth/signup", json=alice)
        create_response = client.post("/journals/?date=2026-01-01&message=hi")
        entry_id = create_response.json()["id"]

        response = client.delete(f"/journals/{entry_id}")

        assert response.status_code == 204
        assert client.get("/journals/").json() == []
