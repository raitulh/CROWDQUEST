# Twitch developer setup

## Application registration

1. Create an application in the Twitch Developer Console.
2. Set the OAuth redirect URL to the exact value in `TWITCH_REDIRECT_URI`.
3. Set the application category and website information required by Twitch.
4. Copy Client ID and Client Secret into the server-side `.env` file.
5. Never expose `TWITCH_CLIENT_SECRET` to the browser or commit `.env`.

Local callback:

```text
http://localhost:8000/api/v1/auth/twitch/callback
```

## OAuth strategy

CrowdQuest uses an authorization-code flow and an installed-chatbot model. The broadcaster authorizes the application with a user token. EventSub WebSocket subscriptions use the broadcaster's user token.

Requested scopes:

- `user:read:chat` — receive chat messages for the authorized broadcaster.
- `user:write:chat` — send concise chat responses as the authorized user.

If chat write permission is not granted, chat reading and game participation can still work; outgoing chat responses are skipped. Add scopes only when a new product feature requires them.

## EventSub

The worker subscribes to:

- Type: `channel.chat.message`
- Version: `1`
- Condition: `broadcaster_user_id` and `user_id` set to the broadcaster's Twitch user ID.
- Transport: WebSocket session ID received from the EventSub welcome message.

The worker handles welcome, notification, keepalive, reconnect, and revocation message types. EventSub message IDs are used for deduplication.

## Chat send

When the broadcaster grants `user:write:chat`, the service uses the Twitch Helix `POST /chat/messages` endpoint. The current user token is used as the sender. The implementation does not assume a separate bot identity.

## Token operations

The application exchanges the authorization code on the backend, validates the token, stores encrypted access and refresh tokens, and refreshes expiring tokens. If refresh fails or Twitch revokes permission, the connection is marked `reauthorization_required` and the user must reconnect.

## Official references

- [Twitch chat authentication](https://dev.twitch.tv/docs/chat/authenticating/)
- [Send and receive chat messages](https://dev.twitch.tv/docs/chat/send-receive-messages/)
- [EventSub subscription management](https://dev.twitch.tv/docs/eventsub/manage-subscriptions/)
- [EventSub WebSocket handling](https://dev.twitch.tv/docs/eventsub/handling-websocket-events/)
- [Twitch OAuth tokens](https://dev.twitch.tv/docs/authentication/getting-tokens-oauth/)
- [Twitch API scopes](https://dev.twitch.tv/docs/authentication/scopes/)
