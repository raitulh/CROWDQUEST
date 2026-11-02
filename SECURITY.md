# Security policy

## Reporting

Do not disclose vulnerabilities publicly before contacting the project maintainers. Provide reproduction steps, affected versions, and impact.

## Security controls in this codebase

- Twitch OAuth authorization-code flow with state verification.
- HttpOnly application session cookie.
- Server-side Twitch credentials.
- Fernet encryption for stored OAuth token material.
- Owner checks for session control APIs and owner WebSockets.
- Unguessable private overlay tokens stored as SHA-256 hashes.
- Database uniqueness constraints for vote/contribution/event idempotency.
- Redis-backed IP rate limiting and short-lived command cooldowns.
- AI proposal schema validation and bounded target/reward values.
- No general raw chat history persistence.

## Deployment obligations

- Use HTTPS and set `COOKIE_SECURE=true`.
- Store secrets in a secret manager, not source control.
- Restrict PostgreSQL and Redis to private networks.
- Rotate credentials after exposure.
- Keep dependencies and container images patched.
- Run dependency, static-analysis, and container scans before releases.
- Add account deletion/data export and retention automation before broad public launch.

The project has not undergone an independent penetration test or formal security certification.
