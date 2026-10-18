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

## Network access

By default the app is reachable from this machine only:

- The backend binds to `127.0.0.1` (`HOST` setting) when run directly.
- `docker-compose.yml` publishes ports `8000` (backend) and `3000` (frontend) on `127.0.0.1` only. Inside the backend container `HOST=0.0.0.0` is required, since the container's own interface is not loopback; the host-side `127.0.0.1:` prefix is what keeps it private.
- Swagger UI is at `/schema/swagger/` and is **unauthenticated**. Set `ENABLE_DOCS=false` to turn it off.
- CORS (`CORS_ALLOWED_ORIGINS`/`CORS_ALLOW_ORIGIN_REGEX`) only controls which web pages a browser lets call the API; it is not access control.

### Running on a server

The frontend is a single-page app, so API calls come from each visitor's browser, not from the frontend server. The backend therefore can't be locked to "the frontend's IP". The usual setup is to keep the backend private and put a reverse proxy in front:

1. Put nginx/Caddy/etc. on the server with HTTPS, serving the frontend and proxying a path such as `/api` to the backend on `127.0.0.1:8000`. Keep the backend port bound to loopback (leave `127.0.0.1:8000:8000` in compose) so the proxy is the only way in.
2. Build the frontend with `VITE_API_BASE_URL` pointing at the public URL, and set `CORS_ALLOWED_ORIGINS` to the frontend's exact origin (e.g. `["https://journal.example.com"]`). Clear or tighten `CORS_ALLOW_ORIGIN_REGEX`, since the default allows any localhost origin.
3. In `.env` set `DEBUG=false`, `SESSION_COOKIE_SECURE=true`, `ENABLE_DOCS=false`.
4. Open only ports 80/443 in the firewall/security group; do not expose 8000 or 3000.
5. To restrict who can use the site, allowlist IPs in the firewall or reverse proxy (e.g. nginx `allow`/`deny`), or put it behind a VPN/Tailscale. Signup is open to anyone who can reach the app, so consider restricting or disabling it if this is a private journal.
