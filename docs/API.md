# API reference

The live OpenAPI contract is available at `/api/openapi.json`. Interactive docs are exposed at `/api/docs` in non-production environments.

## Authentication

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/auth/twitch/login` | Begin Twitch OAuth |
| GET | `/api/v1/auth/twitch/callback` | OAuth callback |
| GET | `/api/v1/auth/status` | Current user and Twitch connection status |
| POST | `/api/v1/auth/logout` | Clear application session cookie |
| POST | `/api/v1/auth/twitch/disconnect` | Stop the EventSub worker from maintaining this connection |

## Sessions

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/v1/sessions` | Create a session and return a private overlay token once |
| GET | `/api/v1/sessions` | List owned sessions |
| GET | `/api/v1/sessions/{id}` | Get current session, round, and vote totals |
| POST | `/api/v1/sessions/{id}/start` | Start session lifecycle |
| POST | `/api/v1/sessions/{id}/quests/generate` | Generate and persist a validated quest proposal |
| POST | `/api/v1/sessions/{id}/voting/start` | Begin voting |
| POST | `/api/v1/sessions/{id}/voting/close` | Close voting early |
| POST | `/api/v1/sessions/{id}/pause` | Pause current gameplay |
| POST | `/api/v1/sessions/{id}/resume` | Resume prior gameplay state |
| POST | `/api/v1/sessions/{id}/end` | End the session |
| POST | `/api/v1/sessions/{id}/overlay-token/rotate` | Revoke old public overlay token and issue a new token |

## Community and analytics

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/community/leaderboard` | Aggregate contribution leaderboard |
| GET | `/api/v1/analytics/summary` | Session-derived summary metrics |
| GET | `/api/v1/settings` | Read user preferences |
| PUT | `/api/v1/settings` | Update user preferences |

## Overlay

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/v1/public/overlays/{token}` | Public, read-only overlay snapshot |
| WS | `/api/v1/public/overlays/ws/{token}` | Public overlay realtime events |
| WS | `/api/v1/public/overlays/owner-ws/{session_id}` | Owner-authenticated live session events |

## Domain event types

`session.started`, `session.paused`, `session.resumed`, `session.ended`, `quest.generated`, `quest.voting_started`, `vote.updated`, `quest.vote_locked`, `quest.selected`, `quest.progress_updated`, and `quest.completed`.
