# CrowdQuest AI — Build and Verification Status

This repository is a production-oriented full application codebase, not a simulated Twitch demo or a minimal UI prototype. It is not represented as a certified, externally deployed, load-tested production service. Real Twitch authorization and deployment verification require credentials and infrastructure owned by the operator.

## Implemented

- Next.js App Router application with a shared Charcoal + Copper + Warm Parchment design system.
- Landing, Twitch login, dashboard, Quest Studio, session list/control center, community leaderboard, analytics, settings, error/loading/not-found screens, and public OBS overlay routes.
- FastAPI application with versioned REST endpoints, health/readiness checks, OpenAPI in non-production environments, request IDs, origin checks, security headers, and Redis-backed rate limiting.
- Twitch authorization-code OAuth flow with one-time Redis state, browser state cookie verification, encrypted access/refresh token storage, token refresh/validation/revocation, and session cookie/JTI revocation.
- Twitch EventSub WebSocket worker for `channel.chat.message`, keepalive/reconnect handling, chat parsing, idempotency, command cooldowns, and rate-gated outbound chat responses.
- PostgreSQL data model and initial Alembic migration for users, Twitch connections, sessions, quest rounds, votes, contributions, processed EventSub events, and persisted session events.
- Redis event fan-out and authenticated owner/public-token WebSocket channels.
- Retention cleanup for processed EventSub IDs and internal session-event records, with indexed cleanup timestamps.
- Deterministic server-authoritative session state machine, unique viewer votes, deterministic tie policy, unique contributions, voting and objective deadlines, pause/resume preservation for both clocks, objective expiry, progression, and transactional XP rewards.
- AI quest composition through Ollama or a configurable OpenAI-compatible chat-completions endpoint, strict Pydantic output validation, and deterministic content fallback when an AI provider is unavailable. This fallback produces quest content only; it does not simulate Twitch traffic or viewers.
- API-driven analytics and contribution leaderboard; empty states are shown when there is no real persisted activity.
- Docker Compose topology for PostgreSQL, Redis, API, EventSub/timer worker, and Next.js web application; Caddy reverse-proxy example; environment bootstrap and production examples.
- CI workflow, backend tests, security notes, API/gameplay/architecture/Twitch/deployment documentation.

## Verification performed in the build environment

The latest verification run completed 19 backend tests successfully, completed PostgreSQL schema migrations with Alembic, and passed Ruff linting with 0 errors. Frontend verification completed `npm install`, TypeScript typechecking with 0 errors, ESLint with 0 errors/warnings, and Next.js production build (`next build`) with 10/10 routes successfully optimized. Both backend FastAPI and frontend Next.js services were verified running live and healthy against real PostgreSQL and Redis instances.

| Check | Result |
|---|---|
| Python compileall | Passed |
| Backend pytest suite | 19 passed |
| Backend Ruff linting | Passed (0 errors) |
| Alembic PostgreSQL migrations | Applied `0001_initial` and `0002_objective_deadlines` cleanly |
| TypeScript/TSX full typecheck (`tsc --noEmit`) | Passed (0 diagnostics) |
| Frontend ESLint (`eslint .`) | Passed (0 errors, 0 warnings) |
| Frontend production build (`next build`) | Passed (10 static/dynamic routes compiled) |
| Local PostgreSQL & Redis readiness (`/health/ready`) | Passed (`database: ok`, `redis: ok`) |
| Live API service (`http://127.0.0.1:8001`) | Running and healthy |
| Live Web service (`http://localhost:3001`) | Running and serving production assets |
| Live Twitch OAuth/EventSub test | Not run: a real Twitch Client ID/Secret, authorized broadcaster account, callback URL, and live channel are required |
| Live AI-provider test | Not run: local Ollama or a configured provider endpoint is required |

## Required operator configuration before connecting a real Twitch channel

1. Install Docker Desktop / Docker Engine with Compose v2.
2. Run `python scripts/bootstrap_env.py` to generate unique local secrets and `.env`.
3. Register a Twitch developer application and configure a callback URI exactly matching `TWITCH_REDIRECT_URI`.
4. Set `TWITCH_CLIENT_ID` and `TWITCH_CLIENT_SECRET` in `.env`.
5. Start Ollama and pull the configured model, or configure an OpenAI-compatible endpoint.
6. Run `docker compose up --build -d` and verify `/health/ready`.
7. Authorize the broadcaster account and test real chat commands on a live Twitch channel.

## Production hardening still required for a public multi-tenant/high-availability rollout

- Generate and commit a `package-lock.json` from a network-enabled build environment, then use `npm ci` in CI and the web Dockerfile. The build container had no registry access, so a truthful lockfile could not be generated here.
- Build and run all containers in the target environment; validate the Caddyfile with the installed Caddy release.
- Run the real Twitch OAuth, EventSub reconnect/revocation, chat send/read, and token refresh acceptance tests with the registered Twitch application.
- Add and verify distributed per-broadcaster worker leases before running more than one EventSub worker replica.
- Add deployment-specific backup/restore drills, metrics/alerts, load tests, secret-manager integration, and security review before a public high-availability launch.
- Review retention requirements and run a data migration strategy before changing the encryption key or database schema.

## No-demo policy

There is no simulated viewer, simulated Twitch connection, fake vote stream, sample analytics feed, or demo-mode switch in the application. A deterministic quest-content fallback is present so gameplay content creation can continue when a configured AI provider is temporarily unavailable. It never fabricates audience activity.
