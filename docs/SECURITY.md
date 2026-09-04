# ChatControl Security

## Authentication Layers

### Layer 1: Twitch OAuth
- Login via Twitch OAuth 2.0
- Scope: `user:read:email`
- Session cookies: HttpOnly, SameSite=Lax, Secure (production)

### Layer 2: Email Verification
- Verification token: SHA-256 hashed, single-use, 15-minute expiry
- Required before linking

### Layer 3: Minecraft Linking
- 6-digit code: CSPRNG generated, SHA-256(salt+code) stored, 60-second TTL
- Single-use, atomic consumption
- Bridge authentication required

## Security Controls

- CSRF protection on all mutating endpoints
- Rate limiting via Flask-Limiter
- Security headers (X-Frame-Options, CSP, nosniff)
- Timing-safe comparisons (hmac.compare_digest)
- Generic error messages (no enumeration)
- One link per streamer (UNIQUE constraint)

## Production Checklist

- [ ] SECRET_KEY is set (not default)
- [ ] FLASK_ENV=production
- [ ] HEARTBEAT_CHECK_SECRET is set
- [ ] ALLOWED_ORIGINS configured
- [ ] HTTPS enabled
- [ ] No secrets in git
