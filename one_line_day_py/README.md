# Backend

Litestar REST API for One Line a Day. Python 3.12+, SQLModel/SQLAlchemy on SQLite, argon2 password hashing, server-side file-backed sessions.

## Run

The supported way to run the full app is Docker from the repo root (see the [main README](../README.md)):

```
docker compose up --build
```

For backend development without Docker:

```
uv sync
cp example.env .env
uv run -m one_line_day_py.main
```

The API is at <http://localhost:8000> and Swagger UI at <http://localhost:8000/schema/swagger/> (when `ENABLE_DOCS=true`).

## Test and lint

```
uv run pytest
uv run ruff check --fix && uv run ruff format
```

Tests use a fresh temporary SQLite database per test (see `tests/test_src/conftest.py`).

## Key behaviours

- Auth is session-cookie based. Journal routes are always scoped to the logged-in user; accessing another user's entry returns 404.
- `GET /journals` accepts optional `month`, `day`, `year` filters, which is how the frontend finds the same day across years.
- Create/update entries take `date` and `message` as query parameters (intentional).
- Users can only update or delete themselves.

## Attachments

Each entry can have up to 5 attachments: images (JPEG, PNG, WebP, GIF, HEIC/HEIF) or PDFs, at most 15 MB each.

| Route | Purpose |
| --- | --- |
| `POST /journals/{entry_id}/attachments/` | Upload one file (multipart, field name `file`) |
| `GET /journals/{entry_id}/attachments/` | List an entry's attachments |
| `GET /journals/{entry_id}/attachments/{id}/thumbnail` | 320×320 WebP thumbnail (`404` for PDFs) |
| `GET /journals/{entry_id}/attachments/{id}/content` | Display-size image (≤2048 px WebP) or the PDF; add `?download=true` to download |
| `DELETE /journals/{entry_id}/attachments/{id}` | Delete one attachment |

- Images are processed once, at upload: EXIF orientation applied, HEIC decoded, GIFs reduced to their first frame. Re-encoding to WebP drops EXIF metadata from what is served. PDFs are stored as-is.
- Entry responses embed attachment metadata (`attachments`, plus `attachments_available`, which is `false` only if the lookup failed; the entries still return `200`).
- Errors: `400` over the 5-file limit, `404` for anything that isn't the caller's (including another user's entry or the wrong `entry_id`), `413` over 15 MB, `415` unsupported type, `422` undecodable image, `503` storage unwritable.
- Deleting an entry deletes its attachment rows (database cascade) and its files. Deleting a user deletes all of their entries, attachment rows and files.
- At startup, any attachment directory whose entry no longer exists is moved to `{ATTACHMENTS_PATH}/.trash/` rather than deleted, so pointing the app at the wrong database can't destroy attachments. Nothing empties the trash yet; clear it by hand once you've checked it.
- Logs never contain filenames, file contents or EXIF, only attachment ids, kind, content type, size and error class. Pillow's loggers are held at `WARNING` because its debug output includes EXIF values.

## Configuration

Set via environment or `.env` (see `example.env`): `DB_PATH`, `ATTACHMENTS_PATH`, `DEBUG`, `LOG_LEVEL`, `SESSION_COOKIE_SECURE`, `CORS_ALLOWED_ORIGINS`, `CORS_ALLOW_ORIGIN_REGEX`, `HOST`, `ENABLE_DOCS`. In production set `DEBUG=false`, `SESSION_COOKIE_SECURE=true`, `ENABLE_DOCS=false`.

`ATTACHMENTS_PATH` is where uploaded photos and PDFs are stored (default `one_line_day_py/src/data/attachments`). It is independent of `DB_PATH`: moving the database does not move attachments. The directory is created on first upload; if it can't be written, the app still starts and uploads return `503`.
