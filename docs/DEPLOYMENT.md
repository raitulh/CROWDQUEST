# Deployment and operations

## Local Docker Compose

Use `python scripts/bootstrap_env.py`, add Twitch credentials to `.env`, then run `docker compose up --build -d`. The API container waits for PostgreSQL and Redis health checks and applies Alembic migrations before starting. The Twitch worker runs separately.

## Production environment

Required production settings:

- `APP_ENV=production`
- Unique `APP_SECRET_KEY` (at least 32 characters)
- Unique Fernet `TOKEN_ENCRYPTION_KEY`
- `COOKIE_SECURE=true`
- HTTPS `FRONTEND_URL`, `BACKEND_URL`, `TWITCH_REDIRECT_URI`, and `NEXT_PUBLIC_API_URL`
- Exact `CORS_ORIGINS`
- Twitch Client ID and Client Secret
- PostgreSQL and Redis credentials supplied from a secret manager
- TLS termination and HSTS at the edge proxy
- API and web host ports restricted to loopback or a private ingress network

The application validates some dangerous production defaults at startup. Deployments must additionally enforce network isolation and secret rotation operationally.

## Reverse proxy

`Caddyfile` is supplied for a Caddy process running on the Docker host. Replace `crowdquest.example.com` with the real hostname and configure the matching frontend/API public URL variables. Caddy routes `/api/*` and `/health/*` to FastAPI and all other routes to Next.js. WebSocket upgrades are handled by Caddy automatically.

The Compose port bindings default to `127.0.0.1` so the API and web server are not directly reachable from the public network. The host reverse proxy can reach those loopback ports. Keep these bindings restricted in production. If you move the proxy into Docker, redesign the network and forwarded-header trust boundary instead of simply exposing the API container.

## Database migrations

Run migrations as part of the release process:

```bash
cd apps/api
alembic upgrade head
```

Do not run schema creation from application startup in production. Create a new Alembic revision for every model change. Back up PostgreSQL before risky migrations and test rollback/restore on a staging copy.

## Process topology

- Web: stateless Next.js process; scale horizontally as needed.
- API: stateless FastAPI processes; scale horizontally behind the reverse proxy.
- PostgreSQL: durable primary database with automated backups and restore tests.
- Redis: authenticated private network service with persistence appropriate to rate-limit and pub/sub operational needs.
- Twitch worker: one active EventSub supervisor replica in this release. Do not scale it horizontally without implementing distributed broadcaster leases and leader election.

## Observability

Collect structured container logs and monitor:
- API request rate, error rate, and latency.
- Database pool saturation and slow queries.
- Redis availability and memory.
- Twitch worker task count and reconnect frequency.
- OAuth status and reauthorization-required accounts.
- EventSub subscription failures/revocations.
- AI provider timeouts and fallback frequency.
- WebSocket connection counts and disconnects.

Never log credentials, tokens, private overlay URLs, or raw chat history.

## Backups and retention

- Enable encrypted PostgreSQL backups and periodically test full restore.
- Redis is not the system of record; loss should not lose committed game state.
- Define a retention period for processed EventSub IDs and session event records before public launch.
- Provide account deletion and data export workflows before broad consumer release.

## Release checklist

- [ ] Secrets loaded from a secret manager.
- [ ] Production cookies are Secure and HttpOnly.
- [ ] CORS is restricted to the public application origin.
- [ ] Twitch callback matches the Developer Console exactly.
- [ ] HTTPS and reverse proxy are verified.
- [ ] Migrations applied and backup verified.
- [ ] Worker has a single active replica.
- [ ] Actual broadcaster OAuth tested.
- [ ] Actual EventSub chat subscription tested.
- [ ] Actual viewer vote and contribution tested.
- [ ] OBS overlay tested in a real broadcast scene.
- [ ] AI provider timeout and fallback tested.
- [ ] Logs and alerts reviewed for secret leakage.
