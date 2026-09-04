# ChatControl API Reference

## Authentication Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | /auth/twitch | None | Redirect to Twitch OAuth |
| GET | /auth/twitch/callback | None | OAuth callback |
| POST | /api/logout | Session+CSRF | Destroy session |

## Email Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /api/email/send | Session+CSRF | Send verification email |
| GET | /api/email/status | Session | Get email verification status |
| POST | /api/email/confirm | Session+CSRF | Confirm email with token |

## Link Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | /api/link/start | Session+CSRF | Generate 6-digit link code |
| GET | /api/link/status | Session | Check linking status |
| POST | /api/link/complete | Bridge token | Complete link (called by Bridge) |
| POST | /api/link/revoke | Session+CSRF | Revoke link |

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| /api/email/send | 3/15min |
| /api/email/confirm | 10/min |
| /api/link/start | 3/min |
| /api/link/complete | 10/min |
| /api/link/revoke | 5/min |
