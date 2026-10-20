# One Line a Day

A pet project by Jonathan Huster: a digital version of the [5 year journal](https://www.amazon.com/One-Line-Day-Five-Year-Memory/dp/0811870197). Write one line per day, and see what you wrote on the same day in previous years.

## Overview

```
 Browser ──► nginx + React SPA (:3000) ──/api/──► Litestar API (:8000) ──► SQLite
              frontend/                            one_line_day_py/         journal_entries.db
```

- **Frontend** (`frontend/`): a React + TypeScript single-page app. Log in, pick a date, and see every entry written on that month/day across all years. Add, edit, and delete entries inline, and attach up to 5 photos or PDFs to each one.
- **Backend** (`one_line_day_py/`): a Litestar (Python) REST API backed by SQLite via SQLModel. Handles signup/login with session cookies and argon2-hashed passwords. Every journal entry and attachment is private to its author. Uploaded files are stored on disk (`ATTACHMENTS_PATH`), with thumbnails and display copies generated at upload.
- **Deployment**: Docker Compose runs both. The frontend's nginx serves the built app and proxies `/api/` to the backend, so the browser only ever talks to one origin.

See the component READMEs for details:

- [Backend README](one_line_day_py/README.md)
- [Frontend README](frontend/README.md)

## How to run

Prerequisite: [Docker](https://docs.docker.com/get-docker/) with Compose.

```
mkdir -p one_line_day_py/src/data/attachments
docker compose up --build
```

The `mkdir` is needed once, before the first run: the attachments directory is bind-mounted, and if it doesn't exist Docker creates it owned by root.

- App: <http://localhost:3000>
- API (debugging only, bound to this machine): <http://localhost:8000>
- Swagger UI: <http://localhost:8000/schema/swagger/>

The SQLite file `one_line_day_py/src/data/journal_entries.db` and the attachments directory `one_line_day_py/src/data/attachments/` (uploaded photos and PDFs) are bind-mounted into the backend container, so your data persists on the host. Back them up together. The attachments location is set by `ATTACHMENTS_PATH`, independently of `DB_PATH`; if you change it, change the container side of the bind mount in `docker-compose.yml` to match.

Configuration is via environment variables in a `.env` file; copy `example.env` to start.

## Contributing

1. Branch from `main` and open a pull request (squash merge preferred).
2. Install [uv](https://docs.astral.sh/uv/) and the tooling and register the git hooks once after cloning:

   ```
   uv sync
   npm --prefix frontend install
   uv run pre-commit install
   ```

   Hooks run on `git push` and merge commits: `ruff` lint/format, backend `pytest`, and frontend `vitest`. To run them manually:

   ```
   uv run pre-commit run --all-files --hook-stage pre-push
   ```

3. Add tests alongside your change (`one_line_day_py/tests/` for the backend, `*.test.ts(x)` next to the module for the frontend).
4. See [`TODO.md`](TODO.md) for the backlog.

Running the pieces without Docker (for development) is covered in the backend and frontend READMEs.

## Network access

With Docker Compose:

- The **frontend** is published on all interfaces (`http://<this-machine-ip>:3000`), so other devices on your network can use the app.
- The **backend** is published on `127.0.0.1:8000` only. The frontend's nginx proxies `/api/` to it over the compose network (`frontend/nginx.conf`), and the frontend is built with `VITE_API_BASE_URL=/api`. Because the browser only talks to port 3000, requests are same-origin and CORS doesn't apply. The `127.0.0.1:8000` mapping is only for debugging and can be removed.
- Swagger UI (`/schema/swagger/`, unauthenticated) is available at `http://localhost:8000` on this machine and is blocked through the proxy. Set `ENABLE_DOCS=false` to turn it off.
- CORS (`CORS_ALLOWED_ORIGINS`/`CORS_ALLOW_ORIGIN_REGEX`) only matters for `npm run dev`, where the frontend (`:5173`) calls the backend (`:8000`) cross-origin. It is not access control.

To make the frontend local-only again, change its port mapping in `docker-compose.yml` to `"127.0.0.1:3000:80"`.

Things to know when the frontend is shared on a network:

- Signup is open, so anyone who can reach port 3000 can create an account. Restrict it if that matters.
- Traffic is plain HTTP; passwords cross the network unencrypted. Use HTTPS (see below) or a VPN such as Tailscale for anything beyond a trusted network.
- On WSL2 the LAN can't see the container ports without Windows port forwarding (`netsh interface portproxy`) or mirrored networking, plus a firewall rule.

### Running on a server

The frontend is a single-page app, so API calls come from each visitor's browser, not from the frontend server. The backend therefore can't be locked to "the frontend's IP". The usual setup is to keep the backend private and put a reverse proxy in front:

1. Keep the compose setup above (frontend nginx proxying `/api/` to a private backend) and put HTTPS in front of port 3000 with Caddy/nginx/a cloud load balancer. Keep the backend port bound to loopback or unpublished.
2. Leave `VITE_API_BASE_URL=/api` so the app stays same-origin and no CORS is needed. Only if you serve the API on a different origin, set `CORS_ALLOWED_ORIGINS` to the frontend's exact origin and tighten `CORS_ALLOW_ORIGIN_REGEX`, since the default allows any localhost origin.
3. In `.env` set `DEBUG=false`, `SESSION_COOKIE_SECURE=true`, `ENABLE_DOCS=false`.
4. Open only ports 80/443 in the firewall/security group; do not expose 8000 or 3000.
5. To restrict who can use the site, allowlist IPs in the firewall or reverse proxy (e.g. nginx `allow`/`deny`), or put it behind a VPN/Tailscale. Signup is open to anyone who can reach the app, so consider restricting or disabling it if this is a private journal.
