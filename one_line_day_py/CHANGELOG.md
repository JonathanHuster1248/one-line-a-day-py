# Changelog

All notable changes to the backend are documented here.

## [0.4.1] - 2026-10-21

Journal entry date conflicts and test coverage.

### Fixed
- Creating a journal entry on a date that already has one, or moving an entry onto such a date, returned `500`. It now returns `409 Conflict` ("An entry already exists for that date") via a new `DuplicateEntryDate` domain exception, and leaves the existing entry unchanged.

### Removed
- The unused `JournalDb.get_entry_author` (the `/journals/{id}/author` route uses `_get_owned_entry`).

### Tests
- Journal controller: create, `409` on duplicate dates for create and update, date changes via `input_date`, empty updates, `400` for missing or malformed params, and `404` for unknown or non-UUID ids.
- `list_entries` filters: month+day across years, year, month alone, Feb 29, out-of-range values, non-integer values, and no leaks between users.

## [0.4.0] - 2026-10-19

Photo and PDF attachments on journal entries.

### Added
- `AttachmentController` at `/journals/{entry_id}/attachments`: upload (multipart, 16 MB request limit), list, thumbnail, content (with `?download=true`) and delete. Every route is scoped to the caller and the entry, with `404` otherwise. File responses are cached `private, immutable` and sent with `nosniff`.
- `AttachmentService` (`src/services/attachments.py`): 5 per entry, 15 MB per file, image/PDF type rule, rollback that leaves no files behind when an upload fails, and a startup sweep that moves orphaned directories to `{ATTACHMENTS_PATH}/.trash/` (never deletes them).
- `src/images.py`: 320×320 WebP thumbnails and ≤2048 px WebP display copies, with EXIF orientation, HEIC support (`pillow-heif`) and first-frame GIFs.
- `AttachmentStorage` (`src/data/attachment_storage.py`) and `AttachmentDb` (`src/data/db.py`).
- `Attachment` / `AttachmentPublic` models, with `ON DELETE CASCADE` from journal entries.
- `ATTACHMENTS_PATH` setting (default `one_line_day_py/src/data/attachments`, independent of `DB_PATH`).
- Domain exceptions mapped to `400`/`413`/`415`/`422`/`503`.
- Dependencies: `pillow`, `pillow-heif`.

### Changed
- Journal responses are `JournalEntryPublic`, adding `attachments` and `attachments_available`. Adding fields is backwards compatible. If the attachment lookup fails, entries still return `200` with `attachments_available: false`.
- Deleting an entry also removes its attachment files.
- Deleting a user also deletes their journal entries, attachment rows (`ON DELETE CASCADE` on `journal_entries.author_id` and `attachments.author_id`) and files. Without this, enabling foreign keys made `DELETE /users/{id}` fail with a `500` for any user with entries. The cascade is part of the schema, so a database created before this release must be recreated for user deletion to work.
- The database's parent directory is created on startup if it doesn't exist.
- SQLite foreign keys are enabled on every connection.
- `docker-compose.yml` bind-mounts the attachments directory, which is also excluded from the Docker build context.
- The `PIL`/`pillow_heif` loggers are held at `WARNING`, so `LOG_LEVEL=DEBUG` can't write EXIF values to the logs.

### Removed
- The unused placeholder `Photo` model.

## [0.3.1] - 2026-10-18

Address lint issues and add CI tooling.

### Added
- `noxfile.py` for running lint and tests with a single command.
- `scripts/check_version_bump.py`, run in CI to fail when backend/frontend code changes without a version bump.
- GitHub Actions workflow (`.github/workflows/pre-commit.yml`) running the pre-commit checks on pull requests.
- `ruff` added to the project requirements.

### Changed
- Pre-commit checks run at the pre-merge stage rather than on push.
- Lint fixes in `controllers/journal.py`, `controllers/user.py`, `data/db.py` and `model.py` (no behavior change).

## [0.3.0] - 2026-10-17

Restrict network access to localhost by default.

### Added
- `HOST` setting (default `127.0.0.1`) controlling the interface uvicorn binds to, replacing the hard-coded `0.0.0.0`.
- `ENABLE_DOCS` setting (default `true`); when `false`, Swagger UI and the OpenAPI schema are not served and `/` returns 404.

### Changed
- `docker-compose.yml` publishes the backend (`8000`) on `127.0.0.1` only (the frontend is reachable on the network and proxies API calls to it, see the frontend changelog), and sets `HOST=0.0.0.0` inside the backend container so the port mapping is what limits exposure.

## [0.2.1] - 2026-10-17

Run lint/format checks on push.

### Changed
- `.pre-commit-config.yaml` now installs and runs the ruff hooks at the `pre-push` stage instead of on commit (`default_install_hook_types`/`default_stages`).

### Added
- Backend unit tests (`pytest`) now run as a `pre-push` hook via a local `pre-commit` hook.
- Frontend tests (`vitest`) run as a `pre-merge-commit` hook.

## [0.2.0] - 2026-10-17

Backend cleanup: session-based auth, controller split, dependency injection, logging.

### Added
- Session-based authentication (`AuthController`: signup/login/logout/me) using Litestar `SessionAuth` with a file-backed session store, and argon2 password hashing (`src/security.py`).
- Per-resource controllers (`RootController`, `UserController`, `JournalController`) split out of the previous monolithic app module, each with dedicated tests under `tests/test_src/test_controllers/`.
- Dependency injection for the database layer (`src/dependencies.py`) to isolate `UserDb`/`JournalDb` construction from `settings`.
- Global exception handling (`src/exceptions.py`) mapping SQLAlchemy's `NoResultFound` to a 404.
- Structured logging (`src/logging_config.py`): console + rotating file handler, with access logs restricted to path/method/status (never bodies, headers, or cookies).
- `DEBUG` setting to control Litestar debug tracebacks per environment.
- Pytest coverage reporting (`pytest-cov`).

### Changed
- Journal entries are now always scoped to the authenticated caller (`request.user.id`); the `author_id` query param was removed.
- Users can no longer modify or delete other users' records (`_check_is_self` permission check).
- Journal entry and user updates no longer accidentally recreate the underlying row.

### Removed
- The JSON-backed data store and its tests, in favor of the SQL-backed implementation.
- Leftover "hello world" example endpoints.
