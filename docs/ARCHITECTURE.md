# Architecture

## System boundaries

### Web application

Next.js is the presentation layer. It owns accessible dashboard interactions, forms, route navigation, and WebSocket rendering. It does not decide whether a vote is valid, compute winners, grant XP, or accept viewer actions as authoritative.

### API

FastAPI exposes versioned REST APIs, OAuth callbacks, owner-authenticated WebSockets, and the public read-only overlay snapshot. It validates ownership for session operations and delegates business rules to domain services.

### Twitch worker

A separate worker process owns EventSub WebSocket connections. It uses broadcaster-authorized user access tokens, receives chat notifications, validates command syntax, and calls the game service. It runs independently of API request workers so a web request restart does not own chat transport state.

The initial deployment uses one worker process. A multi-replica deployment must introduce Redis-backed distributed leases keyed by broadcaster ID before scaling the EventSub supervisor.

### Persistence

PostgreSQL is the source of truth. Unique database constraints enforce one vote per viewer per round, one contribution per viewer and contribution type per round, and one processed EventSub message ID. Redis provides ephemeral coordination, IP rate limiting, OAuth state storage, command cooldowns, and pub/sub fan-out.

### AI boundary

The quest generator accepts a limited creative request and returns a strict `QuestProposal`. All values are validated by Pydantic and the game service. The model cannot change the current session, determine a winner, create a vote, or award XP.

## Realtime flow

1. Twitch sends `channel.chat.message` through EventSub WebSocket.
2. The worker reads the EventSub metadata message ID and chat event.
3. The command parser accepts only allowlisted command forms.
4. The game service locks the relevant PostgreSQL records and applies domain rules.
5. A committed domain event is published to Redis.
6. The API WebSocket layer fans the event out to the session dashboard and overlay.
7. The browser refetches the authoritative snapshot after receiving an event.

## State ownership

- PostgreSQL: identity, tokens (encrypted), sessions, rounds, votes, contributions, session event records.
- Redis: rate limit counters, OAuth state TTL, chat cooldown TTL, ephemeral pub/sub events.
- Browser: ephemeral UI presentation only.
- AI provider: untrusted text proposal only.
