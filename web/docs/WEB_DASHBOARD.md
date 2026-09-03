# ChatControl Web Dashboard

## Architecture

```
Streamer
   |
   v
Web Dashboard (Flask)
   |
   v
Twitch OAuth 2.0
   |
   v
StreamerProfile (SQLite)
   |
   v
Settings -> Bridge -> Twitch -> Minecraft
```

## Setup

### 1. Twitch App Registration

1. Go to https://dev.twitch.tv/console/apps
2. Create a new application
3. Set OAuth Redirect URL: `http://localhost:5000/auth/callback`
4. Copy Client ID and Client Secret

### 2. Environment Variables

```bash
# Required
TWITCH_CLIENT_ID=your_client_id
TWITCH_CLIENT_SECRET=your_client_secret
SECRET_KEY=your_random_secret_key

# Optional
BASE_URL=http://localhost:5000
PORT=5000
DB_PATH=chatcontrol.db
FLASK_DEBUG=1
```

### 3. Install Dependencies

```bash
cd web
pip install -r requirements.txt
```

### 4. Run

```bash
python main.py
```

Dashboard: http://localhost:5000

## OAuth Flow

1. Streamer clicks "Iniciar sesion con Twitch"
2. Redirect to Twitch OAuth authorization
3. Streamer authorizes the app
4. Twitch redirects back with authorization code
5. Backend exchanges code for access token
6. Backend validates token and gets user identity
7. StreamerProfile created/updated in database
8. Web session created with secure cookie

## Security

- OAuth `state` parameter for CSRF protection (random, one-time use)
- Sessions stored in database with expiration
- HttpOnly, SameSite cookies
- Tokens never sent to frontend
- Authorization isolation per streamer

## Database Schema

### streamers
- `twitch_user_id` (PK) - Twitch user ID
- `twitch_login` - Twitch username
- `display_name` - Display name
- `access_token` - OAuth access token
- `refresh_token` - OAuth refresh token
- `minecraft_player` - Target Minecraft player
- `enabled` - System enabled/disabled

### event_settings
- `id` (PK)
- `twitch_user_id` (FK)
- `event_number` (1-10)
- `action` - Action name
- `enabled` - Event enabled/disabled
- `cooldown` - Cooldown in seconds
- `params` - JSON parameters
- `display_name` - Custom display name

### web_sessions
- `session_id` (PK)
- `twitch_user_id` (FK)
- `expires_at` - Expiration timestamp

### oauth_states
- `state` (PK)
- `created_at`
- `used` - One-time use flag

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Redirect to login/dashboard |
| GET | `/login` | Login page |
| GET | `/auth/callback` | Twitch OAuth callback |
| POST | `/logout` | Logout |
| GET | `/dashboard` | Dashboard page |
| GET | `/api/me` | Current user info |
| GET | `/api/settings` | Get all settings |
| PUT | `/api/settings` | Update settings |
| GET | `/api/events` | Get events |
| GET | `/api/events/<n>` | Get single event |
| PUT | `/api/events/<n>` | Update single event |
| PUT | `/api/events/batch` | Batch update events |
