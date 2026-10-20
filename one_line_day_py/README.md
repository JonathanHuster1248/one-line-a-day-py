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

## Configuration

Set via environment or `.env` (see `example.env`): `DB_PATH`, `ATTACHMENTS_PATH`, `DEBUG`, `LOG_LEVEL`, `SESSION_COOKIE_SECURE`, `CORS_ALLOWED_ORIGINS`, `CORS_ALLOW_ORIGIN_REGEX`, `HOST`, `ENABLE_DOCS`. In production set `DEBUG=false`, `SESSION_COOKIE_SECURE=true`, `ENABLE_DOCS=false`.

`ATTACHMENTS_PATH` is where uploaded photos and PDFs are stored (default `one_line_day_py/src/data/attachments`). It is independent of `DB_PATH`: moving the database does not move attachments. The directory is created on first upload; if it can't be written, the app still starts and uploads return `503`.
