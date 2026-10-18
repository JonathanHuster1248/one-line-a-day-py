import sys

import nox

nox.options.default_venv_backend = "uv"
nox.options.sessions = ["tests", "frontend_tests", "version_check"]


@nox.session(python="3.12")
def tests(session: nox.Session) -> None:
    """Backend tests (pytest) in an isolated env built from uv.lock."""
    session.run_install(
        "uv",
        "sync",
        "--locked",
        "--no-default-groups",
        "--group",
        "dev",
        env={"UV_PROJECT_ENVIRONMENT": session.virtualenv.location},
    )
    session.run("pytest", *session.posargs)


@nox.session(venv_backend="none")
def frontend_tests(session: nox.Session) -> None:
    """Frontend tests (Vitest) with a clean, lockfile-exact install."""
    session.run("npm", "--prefix", "frontend", "ci", external=True)
    session.run("npm", "--prefix", "frontend", "run", "test", external=True)


@nox.session(venv_backend="none")
def version_check(session: nox.Session) -> None:
    """Fail if backend/frontend code changed without a version bump."""
    session.run(sys.executable, "scripts/check_version_bump.py")
