# Changelog

All notable changes to the backend are documented here.

## [0.2.1] - 2026-10-17

Run lint/format checks on push.

### Changed
- `.pre-commit-config.yaml` now installs and runs the ruff hooks at the `pre-push` stage instead of on commit (`default_install_hook_types`/`default_stages`).

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
