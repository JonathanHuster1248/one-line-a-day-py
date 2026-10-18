This is a pet project by Jonathan Huster to make a digital one line a day journal book like the [5 year journal](https://www.amazon.com/One-Line-Day-Five-Year-Memory/dp/0811870197). 

To run the main API call 

```
python -m one_line_day_py.main
```

A Docker implementation also exists, with separate images for the backend (`backend.Dockerfile`) and frontend (`frontend/Dockerfile`). Use Docker Compose to build and run both together:

```
docker compose up --build
```

This serves the backend at `http://127.0.0.1:8000` and the frontend at `http://127.0.0.1:3000`, and bind-mounts `one_line_day_py/src/data/journal_entries.db` into the backend container so the database persists on the host.

To run the frontend cd to ./frontend and run 

`npm run dev`

## First-time setup (git hooks)

Linting (ruff), backend tests (pytest) and frontend tests (vitest) run through [pre-commit](https://pre-commit.com) on `git push` and on merge commits. After cloning, install the dependencies the hooks use and register the hooks once:

```
python -m venv .venv
.venv/bin/pip install -e . pre-commit pytest
npm --prefix frontend install
.venv/bin/pre-commit install
```

`pre-commit install` with no flags is enough: `.pre-commit-config.yaml` sets `default_install_hook_types: [pre-push, pre-merge-commit]`, so it installs the pre-push and pre-merge-commit hooks (not a pre-commit hook). To run everything manually without pushing:

```
.venv/bin/pre-commit run --all-files --hook-stage pre-push
```

## Network access

With Docker Compose:

- The **frontend** is published on all interfaces (`http://<this-machine-ip>:3000`), so other devices on your network can use the app.
- The **backend** is published on `127.0.0.1:8000` only. Other devices cannot reach it directly; the frontend's nginx proxies `/api/` to it over the compose network (`frontend/nginx.conf`), and the frontend is built with `VITE_API_BASE_URL=/api`. Because the browser only ever talks to port 3000, requests are same-origin and CORS doesn't apply. The `127.0.0.1:8000` mapping is only for debugging and can be removed.
- Swagger UI (`/schema/swagger/`, unauthenticated) is available at `http://localhost:8000` on this machine and is blocked through the proxy. Set `ENABLE_DOCS=false` to turn it off.
- Run directly (`python -m one_line_day_py.main`), the backend binds to `127.0.0.1` (`HOST` setting). Inside the container `HOST=0.0.0.0` is required because the container's own interface is not loopback.
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
