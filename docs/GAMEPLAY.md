# Gameplay rules

## Session lifecycle

`created → ready → voting → active → ready → ... → ended`

A session is created for an authenticated Twitch broadcaster. A quest round is generated and persisted before voting begins. The streamer can start/close voting, pause/resume the session, and end the session.

## Quest round lifecycle

`ready → voting → active → completed | failed`

A round with zero votes becomes `failed` and the session returns to `ready`. The streamer can then compose another round. An active objective also fails when its server-side deadline expires.

## Voting

- Only `!vote 1`, `!vote 2`, or `!vote 3` are accepted.
- The session and round must be in `voting` state.
- The deadline is checked by the domain service, not the browser.
- The first accepted vote from a Twitch user ID is final for that round.
- A unique database constraint is the final duplicate-vote guard.
- The timer worker closes expired votes.
- A streamer may close voting early.
- A tie is resolved deterministically by the lowest option ID; this is disclosed in the API event.
- A round with no votes fails rather than inventing a winner.

## Community objective

After a winner is selected, the chosen option defines an objective type, validated target, and objective duration (30–600 seconds). `!help` contributes one unit per Twitch user ID for the round. The contribution uniqueness constraint prevents repeated progress farming. The domain service checks the objective deadline at the time of each contribution, and a background worker also closes expired objectives. Contribution, progress, XP, and completion state are committed transactionally.

## Pausing

The session stores the prior `voting` or `active` state and the remaining time when paused. Timer processing and chat actions do not advance while paused. Resume restores the previous state and remaining countdown.

## Rewards

Each accepted `!help` contribution awards 5 participation XP. Completing the objective awards the validated round reward to the session's community XP. The current leaderboard aggregates persisted contribution XP by viewer. Reward and contribution uniqueness is enforced by the database.

## AI contract

AI generates exactly three option proposals. Option IDs must be 1, 2, and 3; objective types are allowlisted; target values are limited to 3–1000; objective duration is limited to 30–600 seconds; reward XP is limited to 20–1000. The game service consumes validated proposals only.
