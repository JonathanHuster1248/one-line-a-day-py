"""Fail if backend/frontend code changed without a version bump.

Compares the working tree against a base ref (default: origin/main, falling back
to main; override with VERSION_CHECK_BASE). Backend version lives in
pyproject.toml, frontend version in frontend/package.json.
"""

import json
import os
import re
import subprocess
import sys
import tomllib

# (name, version file, path prefixes whose changes require a bump, paths that don't count)
COMPONENTS = [
    (
        "backend",
        "pyproject.toml",
        ("one_line_day_py/", "backend.Dockerfile"),
        ("one_line_day_py/tests/", "tests/"),
    ),
    (
        "frontend",
        "frontend/package.json",
        ("frontend/",),
        (
            "frontend/package.json",
            "frontend/package-lock.json",
            "frontend/CHANGELOG.md",
            "frontend/README.md",
        ),
    ),
]


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], check=True, capture_output=True, text=True
    ).stdout


def resolve_base() -> str:
    if base := os.environ.get("VERSION_CHECK_BASE"):
        return base
    for ref in ("origin/main", "main"):
        if (
            subprocess.run(
                ["git", "rev-parse", "--verify", "-q", ref],
                check=False,
                capture_output=True,
            ).returncode
            == 0
        ):
            return ref
    sys.exit("version check: cannot find origin/main or main to compare against")


def parse_version(text: str, path: str) -> str:
    if path.endswith(".toml"):
        return tomllib.loads(text)["project"]["version"]
    return json.loads(text)["version"]


def as_tuple(version: str) -> tuple[int, ...]:
    return tuple(int(p) for p in re.findall(r"\d+", version))


def is_test(path: str) -> bool:
    return bool(re.search(r"\.test\.[jt]sx?$|/test_[^/]*\.py$|/src/test/", path))


def main() -> int:
    base = resolve_base()
    changed = git("diff", "--name-only", base).splitlines()
    failed = False

    for name, version_file, prefixes, ignored in COMPONENTS:
        relevant = [
            f
            for f in changed
            if f.startswith(prefixes)
            and not f.startswith(ignored)
            and not f.endswith(".md")
            and not is_test(f)
            and "/node_modules/" not in f
            and not f.startswith("frontend/dist/")
        ]
        if not relevant:
            continue

        with open(version_file) as fh:
            new = parse_version(fh.read(), version_file)
        old = parse_version(git("show", f"{base}:{version_file}"), version_file)

        if as_tuple(new) <= as_tuple(old):
            failed = True
            print(
                f"{name}: code changed but version in {version_file} is {new} "
                f"(base {base}: {old}). Bump it.\n  changed: {', '.join(relevant[:5])}"
                + (" ..." if len(relevant) > 5 else "")
            )
        else:
            print(f"{name}: version bumped {old} -> {new}")

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
