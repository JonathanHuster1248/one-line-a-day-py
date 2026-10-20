import io
from pathlib import Path

import pytest
from litestar import Litestar
from litestar.testing import TestClient
from PIL import Image

from one_line_day_py.src.services.attachments import MAX_FILE_BYTES

PDF = b"%PDF-1.4\n%fake\n"


def png(size: tuple[int, int] = (640, 480)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, "red").save(buf, format="PNG")
    return buf.getvalue()


def stored_files(app: Litestar) -> list[Path]:
    root: Path = app.state.attachment_service.storage.root
    return [p for p in root.rglob("*") if p.is_file()] if root.exists() else []


def create_entry(client: TestClient, day: str = "2026-01-01") -> str:
    return client.post(f"/journals/?date={day}&message=hi").json()["id"]


def upload(
    client: TestClient,
    entry_id: str,
    data: bytes | None = None,
    filename: str = "photo.png",
    content_type: str = "image/png",
):
    return client.post(
        f"/journals/{entry_id}/attachments/",
        files={"file": (filename, data if data is not None else png(), content_type)},
    )


@pytest.fixture
def alice_client(app: Litestar, alice):
    with TestClient(app=app) as c:
        c.post("/auth/signup", json=alice)
        yield c


@pytest.fixture
def bob_client(app: Litestar, bob):
    with TestClient(app=app) as c:
        c.post("/auth/signup", json=bob)
        yield c


class TestUpload:
    def test_upload_image(self, alice_client):
        entry_id = create_entry(alice_client)

        response = upload(alice_client, entry_id)

        assert response.status_code == 201
        body = response.json()
        assert body["entry_id"] == entry_id
        assert body["filename"] == "photo.png"
        assert body["kind"] == "image"
        assert body["content_type"] == "image/webp"
        assert body["has_thumbnail"] is True
        assert (body["width"], body["height"]) == (640, 480)

    def test_upload_pdf(self, alice_client):
        entry_id = create_entry(alice_client)

        response = upload(alice_client, entry_id, PDF, "doc.pdf", "application/pdf")

        assert response.status_code == 201
        assert response.json()["kind"] == "pdf"
        assert response.json()["has_thumbnail"] is False

    def test_listed_in_upload_order(self, alice_client):
        entry_id = create_entry(alice_client)
        first = upload(alice_client, entry_id, filename="a.png").json()["id"]
        second = upload(alice_client, entry_id, PDF, "b.pdf", "application/pdf")

        response = alice_client.get(f"/journals/{entry_id}/attachments/")

        assert response.status_code == 200
        assert [a["id"] for a in response.json()] == [first, second.json()["id"]]

    def test_sixth_upload_rejected_and_leaves_nothing(self, app, alice_client):
        entry_id = create_entry(alice_client)
        for _ in range(5):
            assert upload(alice_client, entry_id).status_code == 201
        files_before = stored_files(app)

        response = upload(alice_client, entry_id)

        assert response.status_code == 400
        assert stored_files(app) == files_before
        assert len(alice_client.get(f"/journals/{entry_id}/attachments/").json()) == 5

    def test_over_size_limit(self, app, alice_client):
        entry_id = create_entry(alice_client)

        response = upload(alice_client, entry_id, b"\0" * (MAX_FILE_BYTES + 1))

        assert response.status_code == 413
        assert stored_files(app) == []

    def test_unsupported_type(self, alice_client):
        entry_id = create_entry(alice_client)

        response = upload(alice_client, entry_id, b"hello", "notes.txt", "text/plain")

        assert response.status_code == 415

    def test_undecodable_image_leaves_nothing(self, app, alice_client):
        entry_id = create_entry(alice_client)

        response = upload(alice_client, entry_id, b"not an image")

        assert response.status_code == 422
        assert stored_files(app) == []
        assert alice_client.get(f"/journals/{entry_id}/attachments/").json() == []

    def test_wrong_field_name_rejected(self, alice_client):
        entry_id = create_entry(alice_client)

        response = alice_client.post(
            f"/journals/{entry_id}/attachments/",
            files={"upload": ("photo.png", png(), "image/png")},
        )

        assert response.status_code == 400

    def test_missing_entry_is_404(self, alice_client):
        response = upload(alice_client, "00000000-0000-0000-0000-000000000000")

        assert response.status_code == 404


class TestServe:
    def test_thumbnail_is_320_square(self, alice_client):
        entry_id = create_entry(alice_client)
        attachment_id = upload(alice_client, entry_id).json()["id"]

        response = alice_client.get(
            f"/journals/{entry_id}/attachments/{attachment_id}/thumbnail"
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/webp"
        assert Image.open(io.BytesIO(response.content)).size == (320, 320)

    def test_pdf_has_no_thumbnail(self, alice_client):
        entry_id = create_entry(alice_client)
        attachment_id = upload(
            alice_client, entry_id, PDF, "doc.pdf", "application/pdf"
        ).json()["id"]

        response = alice_client.get(
            f"/journals/{entry_id}/attachments/{attachment_id}/thumbnail"
        )

        assert response.status_code == 404

    def test_image_content_is_inline_display_copy(self, alice_client):
        entry_id = create_entry(alice_client)
        attachment_id = upload(alice_client, entry_id).json()["id"]

        response = alice_client.get(
            f"/journals/{entry_id}/attachments/{attachment_id}/content"
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "image/webp"
        assert response.headers["content-disposition"].startswith("inline")
        assert Image.open(io.BytesIO(response.content)).size == (640, 480)

    def test_pdf_content_served_as_is(self, alice_client):
        entry_id = create_entry(alice_client)
        attachment_id = upload(
            alice_client, entry_id, PDF, "doc.pdf", "application/pdf"
        ).json()["id"]

        response = alice_client.get(
            f"/journals/{entry_id}/attachments/{attachment_id}/content"
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content == PDF

    def test_download_disposition_uses_escaped_filename(self, alice_client):
        entry_id = create_entry(alice_client)
        attachment_id = upload(
            alice_client, entry_id, PDF, 'my "trip"\r\nX-Evil: 1.pdf', "application/pdf"
        ).json()["id"]

        response = alice_client.get(
            f"/journals/{entry_id}/attachments/{attachment_id}/content?download=true"
        )

        disposition = response.headers["content-disposition"]
        assert disposition.startswith("attachment")
        assert "x-evil" not in response.headers
        assert "\r" not in disposition and "\n" not in disposition
        assert '"trip"' not in disposition

    @pytest.mark.parametrize("variant", ["thumbnail", "content"])
    def test_caching_headers(self, alice_client, variant):
        entry_id = create_entry(alice_client)
        attachment_id = upload(alice_client, entry_id).json()["id"]

        response = alice_client.get(
            f"/journals/{entry_id}/attachments/{attachment_id}/{variant}"
        )

        assert (
            response.headers["cache-control"] == "private, max-age=31536000, immutable"
        )
        assert response.headers["x-content-type-options"] == "nosniff"

    def test_missing_file_on_disk_is_404(self, app, alice_client):
        entry_id = create_entry(alice_client)
        attachment_id = upload(alice_client, entry_id).json()["id"]
        for path in stored_files(app):
            path.unlink()

        base = f"/journals/{entry_id}/attachments/{attachment_id}"
        assert alice_client.get(f"{base}/thumbnail").status_code == 404
        assert alice_client.get(f"{base}/content").status_code == 404
        assert alice_client.get(f"/journals/{entry_id}").status_code == 200


class TestDelete:
    def test_delete_removes_row_and_files(self, app, alice_client):
        entry_id = create_entry(alice_client)
        attachment_id = upload(alice_client, entry_id).json()["id"]

        response = alice_client.delete(
            f"/journals/{entry_id}/attachments/{attachment_id}"
        )

        assert response.status_code == 204
        assert alice_client.get(f"/journals/{entry_id}/attachments/").json() == []
        assert stored_files(app) == []

    def test_delete_missing_is_404(self, alice_client):
        entry_id = create_entry(alice_client)

        response = alice_client.delete(
            f"/journals/{entry_id}/attachments/00000000-0000-0000-0000-000000000000"
        )

        assert response.status_code == 404


class TestAccess:
    def test_unauthenticated_gets_401(self, app, alice_client):
        entry_id = create_entry(alice_client)
        attachment_id = upload(alice_client, entry_id).json()["id"]
        base = f"/journals/{entry_id}/attachments"

        with TestClient(app=app) as anon:
            assert upload(anon, entry_id).status_code == 401
            assert anon.get(f"{base}/").status_code == 401
            assert anon.get(f"{base}/{attachment_id}/thumbnail").status_code == 401
            assert anon.get(f"{base}/{attachment_id}/content").status_code == 401
            assert anon.delete(f"{base}/{attachment_id}").status_code == 401

    def test_other_user_gets_404_everywhere(self, app, alice_client, bob_client):
        entry_id = create_entry(alice_client)
        attachment_id = upload(alice_client, entry_id).json()["id"]
        base = f"/journals/{entry_id}/attachments"

        assert upload(bob_client, entry_id).status_code == 404
        assert bob_client.get(f"{base}/").json() == []
        assert bob_client.get(f"{base}/{attachment_id}/thumbnail").status_code == 404
        assert bob_client.get(f"{base}/{attachment_id}/content").status_code == 404
        assert bob_client.delete(f"{base}/{attachment_id}").status_code == 404

        assert len(alice_client.get(f"{base}/").json()) == 1
        assert len(stored_files(app)) == 2

    def test_cross_entry_access_is_404(self, alice_client, bob_client):
        alice_entry = create_entry(alice_client)
        attachment_id = upload(alice_client, alice_entry).json()["id"]
        bob_entry = create_entry(bob_client)
        base = f"/journals/{bob_entry}/attachments/{attachment_id}"

        assert bob_client.get(f"{base}/thumbnail").status_code == 404
        assert bob_client.get(f"{base}/content").status_code == 404
        assert bob_client.delete(base).status_code == 404

    def test_own_attachment_through_own_other_entry_is_404(self, alice_client):
        entry_id = create_entry(alice_client, "2026-01-01")
        other_entry = create_entry(alice_client, "2025-01-01")
        attachment_id = upload(alice_client, entry_id).json()["id"]

        response = alice_client.get(
            f"/journals/{other_entry}/attachments/{attachment_id}/thumbnail"
        )

        assert response.status_code == 404
