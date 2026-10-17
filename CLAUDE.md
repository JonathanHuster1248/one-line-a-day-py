# Project Overview
A backend and frontend journal application that enables the addition of new journal entries and displays values by day of year so you can see previous year's journal entries for the same day. Entries are private per-user behind session-based authentication.

## Commands
- Dev frontend: `npm run dev` (run from `frontend/`)
- Build frontend: `npm run build` (run from `frontend/`)
- Dev backend: `.venv/bin/python -m one_line_day_py.main`
- Backend tests: `.venv/bin/pytest` (coverage via `pytest-cov`, see `.coverage`)
- Lint/format (backend): `ruff check --fix` / `ruff format`, wired up as pre-commit hooks (`.pre-commit-config.yaml`)
- Full stack via Docker: `docker compose up --build` — backend on `http://localhost:8000`, frontend on `http://localhost:3000`

## Structure

### Backend (`one_line_day_py/`)
Python 3.12+, using Litestar (API framework) + SQLModel/SQLAlchemy (ORM) + uvicorn + argon2 (password hashing).
- `main.py` — app factory (`make_app`) and uvicorn entrypoint. Registers `AuthController`, `RootController`, `JournalController`, `UserController`. Wires up `SessionAuth` (Litestar session auth) with a server-side, file-backed session store (`FileStore`, stored alongside the DB in a `.sessions` dir), global `exception_handlers`, CORS from `settings` (no longer wide open), and logging (`create_logging_config`/`logging_middleware_config` from `src/logging_config.py`). `debug=settings.debug` (set `DEBUG=false` in prod to disable Litestar's debug tracebacks). `/schema`, `/favicon.ico`, and `/ping` are excluded from both session auth and access logging.
- `src/controllers/` — Litestar controllers, one per resource, re-exported via `__init__.py`:
  - `RootController` (`/`) — redirect to Swagger docs, favicon, and `/ping` (unauthenticated health check, returns `{"status": "ok"}`).
  - `AuthController` (`/auth`) — `signup`, `login`, `logout`, `me`. Signup/login/logout are excluded from auth; sets/clears the session cookie (`user_id`). Also exports `retrieve_user_handler`, used by `SessionAuth` to resolve `request.user` from the session on every authenticated request.
  - `UserController` (`/users`) — CRUD for users (list, get by id, get by name, update, delete). Update/delete enforce the caller can only modify their own record (`_check_is_self`, raises `PermissionDeniedException` otherwise).
  - `JournalController` (`/journals`) — CRUD for journal entries, always scoped to `request.user.id` (no `author_id` query param anymore — entries are implicitly the caller's). `list_entries` supports optional `month`, `day`, `year` query filters (used to find same-day-across-years entries). Per-entry routes (`get`/`update`/`delete`) 404 if the entry isn't owned by the caller (`_get_owned_entry`).
  - Note: db instances (`dependencies.users_db`, `dependencies.journals_db`) are module-level singletons, not dependency-injected (see TODO comments in `dependencies.py` and `journal.py`).
- `src/dependencies.py` — constructs the `UserDb`/`JournalDb` singletons from `settings.db_path` at import time.
- `src/exceptions.py` — global exception handler mapping SQLAlchemy's `NoResultFound` to a `404 NotFoundException`.
- `src/logging_config.py` — `create_logging_config()` builds the Litestar `LoggingConfig` (console + a `RotatingFileHandler` writing to `.logs/app.log`, next to `.sessions`; level from `settings.log_level`); `logging_middleware_config` is the `LoggingMiddlewareConfig` for access logs, which deliberately logs only `path`/`method`/`status_code` — never request/response bodies, headers, or cookies, since those can carry passwords or private journal text.
- `src/security.py` — `hash_password`/`verify_password` using argon2 (`argon2-cffi`).
- `src/schemas.py` — `SignupPayload`/`LoginPayload` request models, `to_public_user` mapper (strips `hashed_password` before returning a `User`).
- `src/model.py` — SQLModel table definitions: `User` (now includes `hashed_password`), `UserPublic` (safe-to-return projection, no password), `JournalEntry` (unique on `author_id`+`date`), `Photo` (defined but not yet wired to any controller).
- `src/settings.py` — `CoreSettings` (pydantic-settings), loads `.env` via `python-dotenv`. Fields: `db_path` (default `one_line_day_py/src/data/journal_entries.db`), `debug` (default `True`; set `false` in prod to disable Litestar debug tracebacks), `session_cookie_secure` (set `true` in prod/HTTPS), `cors_allowed_origins`, `cors_allow_origin_regex` (defaults to permitting any `localhost`/`127.0.0.1` origin/port for local dev), `log_level` (default `"INFO"`, see logging setup in `main.py`).
- `src/data/db.py` — `UserDb` / `JournalDb`: the SQLAlchemy/SQLModel-backed data layer used by the controllers.
- `tests/test_src/` — pytest tests: `test_controllers/` (`test_auth.py`, `test_user.py`, `test_journal.py`, `test_root.py`) and `test_security.py`. `conftest.py` provides `app`/`client` fixtures (fresh tmp-path SQLite DB per test via `monkeypatch`, with `dependencies.users_db`/`journals_db` repointed at it) plus `alice`/`bob` sample signup payloads for multi-user auth tests.
- Swagger UI is available at `/schema/swagger/` when the server is running.

### Frontend (`frontend/`)
React 19 + TypeScript, built with Vite.
- `src/main.tsx` — mounts `<App />` (wrapped in `<AuthProvider>`) into `#root`.
- `src/App.tsx` — gated by auth: renders `<AuthForms />` while logged out, otherwise the journal UI. The journal UI has a date picker with prev/next day and prev/next year navigation, lists same-day entries (`JournalBox` per entry) for the selected month/day, and supports inline create/edit/delete plus logout.
- `src/AuthContext.tsx` — React context (`AuthProvider`/`useAuth`) exposing `user`, `loading`, `login`, `signup`, `logout`; loads the current user on mount via `getCurrentUser`.
- `src/AuthForms.tsx` — combined login/signup form UI, toggles between modes.
- `src/auth.ts` — API client for `/auth/*` (`signup`, `login`, `logout`, `getCurrentUser`); all calls use `credentials: "include"` so the session cookie is sent/stored.
- `src/config.ts` — `API_BASE_URL`, read from `VITE_API_BASE_URL` (falls back to `http://localhost:8000`).
- `src/greeting.ts` — API client functions for journals (`getJournal`, `getJournals`, `createJournalEntry`, `updateJournalEntry`, `deleteJournalEntry`). Note there's still a duplicate `Journal` interface here and in `models.ts` — `models.ts`'s version remains unused (import is commented out).
- `src/models.ts` — shared `Journal` type (still not consistently used — see above).
- No routing or state management library yet; state is local `useState`/`useEffect` in `App.tsx`/`AuthContext.tsx`.

### Cross-cutting notes
- No shared type generation between backend and frontend — the `Journal` TS interface is hand-kept in sync with the `JournalEntry` SQLModel.
- Frontend API base URL is configurable via `VITE_API_BASE_URL` (defaults to `localhost:8000`; set as a Docker build arg in `frontend/Dockerfile`/`docker-compose.yml`).
- Auth is server-side session based (Litestar `SessionAuth` + signed session cookie), not token-based. `SESSION_COOKIE_SECURE` should be `true` in production (HTTPS). CORS is restricted via `CORS_ALLOWED_ORIGINS`/`CORS_ALLOW_ORIGIN_REGEX` rather than wide open.
- `example.env` documents the env vars (`DB_PATH`, `DEBUG`, `LOG_LEVEL`, `SESSION_COOKIE_SECURE`, `CORS_ALLOWED_ORIGINS`, `CORS_ALLOW_ORIGIN_REGEX`); `.env` is loaded automatically via `python-dotenv`.
- `backend.Dockerfile` (Ubuntu + `uv`, installs the package, runs via `uv run -m one_line_day_py.main`, exposes 8000) and `frontend/Dockerfile` (multi-stage Node build → nginx, exposes 80) exist for containerized runs; `docker-compose.yml` builds/runs both together and bind-mounts the SQLite DB file into the backend container so it persists on the host.
- `TODO.md` tracks outstanding work (photos feature, FE polish, CI/deploy, docs); treat it as the current backlog rather than this file duplicating it.
