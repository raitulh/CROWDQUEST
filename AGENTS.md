# CrowdQuest AI — Engineering Constitution

## Product contract
CrowdQuest AI turns real Twitch chat events into deterministic cooperative gameplay. It is not a chatbot, simulated stream, or local-only toy.

## Architecture boundaries
- `apps/web`: Next.js presentation and browser-side state only.
- `apps/api`: FastAPI application, authorization, domain services, persistence, Twitch adapters, and realtime APIs.
- `twitch-worker`: the single EventSub connection supervisor and voting timer process.
- PostgreSQL is the source of truth for identity, sessions, rounds, votes, contributions, and event records.
- Redis is used for ephemeral coordination, rate limiting, and realtime fan-out; it is not the source of truth.
- AI produces untrusted structured content proposals. The game engine validates and owns every gameplay transition.

## Mandatory rules
1. Do not add demo mode, fake Twitch connections, simulated viewers, mock vote data, or fabricated analytics.
2. Never accept viewer gameplay actions from an unauthenticated browser request. Viewer actions must originate from verified Twitch EventSub messages.
3. Never trust model-generated targets, identifiers, states, rewards, or instructions without schema and domain validation.
4. Never expose Twitch access tokens, refresh tokens, client secrets, encryption keys, or private overlay tokens in logs or client bundles.
5. Use database transactions and uniqueness constraints for votes, contributions, processed events, and rewards.
6. Keep Twitch I/O, AI provider I/O, game rules, persistence, and UI separated.
7. Maintain the Charcoal + Copper + Warm Parchment visual system consistently across every route and OBS overlay.
8. No feature is complete until its failure behaviour and tests are addressed.
9. Do not mark real Twitch integration as verified unless it has been tested with a real developer application and authorized channel.
10. Update documentation and migrations with every architectural change.

## Engineering standards
- Python: type hints, async I/O, Pydantic validation, SQLAlchemy 2.x, Ruff.
- TypeScript: strict mode, typed API contracts, accessible controls.
- No silent exception swallowing except where a boundary intentionally degrades with an observable log and status.
- Keep production configuration fail-closed.
- Prefer additive database migrations and backwards-compatible API changes.

## Design standards
- Background: `#211E1A`.
- Surfaces: `#302A23`, `#393127`.
- Warm parchment: `#F6F0E6`, `#E9DECC`.
- Copper: `#A56A45`, `#C28A54`.
- Gold: `#D1A76A`.
- No generic blue SaaS styling, neon purple, excessive glassmorphism, or unrelated stock art.
