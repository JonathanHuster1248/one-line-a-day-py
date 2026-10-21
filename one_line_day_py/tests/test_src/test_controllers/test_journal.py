from uuid import uuid4

import pytest
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

    def test_create_returns_the_new_entry(self, client, alice):
        me = client.post("/auth/signup", json=alice).json()

        response = client.post("/journals/?date=2026-01-01&message=hi")

        assert response.status_code == 201
        body = response.json()
        assert body["author_id"] == me["id"]
        assert body["date"] == "2026-01-01"
        assert body["message"] == "hi"
        assert client.get(f"/journals/{body['id']}").json() == body

    def test_create_on_a_taken_date_is_a_conflict(self, client, alice):
        client.post("/auth/signup", json=alice)
        client.post("/journals/?date=2026-01-01&message=first")

        response = client.post("/journals/?date=2026-01-01&message=second")

        assert response.status_code == 409
        [entry] = client.get("/journals/").json()
        assert entry["message"] == "first"

    def test_different_users_can_write_on_the_same_date(self, app, alice, bob):
        with TestClient(app=app) as alice_client, TestClient(app=app) as bob_client:
            alice_client.post("/auth/signup", json=alice)
            bob_client.post("/auth/signup", json=bob)

            assert (
                alice_client.post("/journals/?date=2026-01-01&message=a").status_code
                == 201
            )
            assert (
                bob_client.post("/journals/?date=2026-01-01&message=b").status_code
                == 201
            )

    @pytest.mark.parametrize(
        "query",
        [
            "date=not-a-date&message=hi",
            "date=2026-02-30&message=hi",
            "message=hi",
            "date=2026-01-01",
        ],
    )
    def test_create_with_missing_or_malformed_params_is_rejected(
        self, client, alice, query
    ):
        client.post("/auth/signup", json=alice)

        assert client.post(f"/journals/?{query}").status_code == 400
        assert client.get("/journals/").json() == []

    def test_owner_can_move_entry_to_another_date(self, client, alice):
        client.post("/auth/signup", json=alice)
        entry_id = client.post("/journals/?date=2026-01-01&message=hi").json()["id"]

        response = client.put(f"/journals/{entry_id}?input_date=2026-01-02")

        assert response.status_code == 200
        assert response.json()["date"] == "2026-01-02"
        assert response.json()["message"] == "hi"

    def test_update_with_no_fields_changes_nothing(self, client, alice):
        client.post("/auth/signup", json=alice)
        created = client.post("/journals/?date=2026-01-01&message=hi").json()

        response = client.put(f"/journals/{created['id']}")

        assert response.status_code == 200
        assert response.json() == created

    def test_moving_entry_onto_a_taken_date_is_a_conflict(self, client, alice):
        client.post("/auth/signup", json=alice)
        client.post("/journals/?date=2026-01-01&message=first")
        entry_id = client.post("/journals/?date=2026-01-02&message=second").json()["id"]

        response = client.put(f"/journals/{entry_id}?input_date=2026-01-01&message=x")

        assert response.status_code == 409
        unchanged = client.get(f"/journals/{entry_id}").json()
        assert unchanged["date"] == "2026-01-02"
        assert unchanged["message"] == "second"

    @pytest.mark.parametrize("method", ["get", "put", "delete"])
    def test_unknown_entry_is_404(self, client, alice, method):
        client.post("/auth/signup", json=alice)

        response = getattr(client, method)(f"/journals/{uuid4()}")

        assert response.status_code == 404

    def test_non_uuid_entry_id_is_404(self, client, alice):
        client.post("/auth/signup", json=alice)

        assert client.get("/journals/not-a-uuid").status_code == 404


class TestListEntriesFilters:
    DATES = ("2024-02-29", "2024-03-01", "2025-03-01", "2026-03-01", "2026-03-02")

    @pytest.fixture
    def dated_client(self, client, alice):
        client.post("/auth/signup", json=alice)
        for d in self.DATES:
            assert client.post(f"/journals/?date={d}&message={d}").status_code == 201
        return client

    @staticmethod
    def _dates(client, query=""):
        return sorted(e["date"] for e in client.get(f"/journals/?{query}").json())

    def test_no_filters_returns_everything(self, dated_client):
        assert self._dates(dated_client) == list(self.DATES)

    def test_month_and_day_match_across_years(self, dated_client):
        assert self._dates(dated_client, "month=3&day=1") == [
            "2024-03-01",
            "2025-03-01",
            "2026-03-01",
        ]

    def test_year_narrows_to_one_year(self, dated_client):
        assert self._dates(dated_client, "month=3&day=1&year=2025") == ["2025-03-01"]
        assert self._dates(dated_client, "year=2026") == ["2026-03-01", "2026-03-02"]

    def test_month_alone(self, dated_client):
        assert self._dates(dated_client, "month=2") == ["2024-02-29"]

    def test_leap_day(self, dated_client):
        assert self._dates(dated_client, "month=2&day=29") == ["2024-02-29"]

    @pytest.mark.parametrize(
        "query", ["month=13", "day=32", "month=6&day=15", "year=1999"]
    )
    def test_no_match_is_empty(self, dated_client, query):
        assert dated_client.get(f"/journals/?{query}").json() == []

    def test_non_integer_filter_is_rejected(self, dated_client):
        assert dated_client.get("/journals/?month=march").status_code == 400

    def test_filters_never_cross_users(self, app, dated_client, bob):
        with TestClient(app=app) as bob_client:
            bob_client.post("/auth/signup", json=bob)
            assert bob_client.get("/journals/?month=3&day=1").json() == []
