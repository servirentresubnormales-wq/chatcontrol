# ChatControl Web Frontend

## Overview

Static frontend for ChatControl built with [Astro](https://astro.build/). Deployed to GitHub Pages. Connects to Flask backend API for real data with fallback to mock data.

## Framework

- **Astro 5.x** — Static site generator with minimal JavaScript
- **TypeScript** — Type safety
- **GitHub Pages** — Static hosting
- **Flask Backend** — API at configurable URL via `PUBLIC_API_URL`

## Structure

```
site/
├── src/
│   ├── pages/
│   │   ├── index.astro       Landing page
│   │   ├── dashboard.astro   Streamer dashboard (API + mock fallback)
│   │   └── login.astro       Twitch OAuth redirect
│   ├── components/
│   │   ├── Header.astro      Navigation header
│   │   ├── Footer.astro      Site footer
│   │   └── EventCard.astro   Editable event card with API toggle
│   ├── layouts/
│   │   └── Layout.astro      Base HTML layout
│   ├── lib/
│   │   ├── config.ts         API_URL from env var
│   │   └── api.ts            API client with CSRF support
│   └── data/
│       └── mock.ts           Mock data for demo mode fallback
├── public/
│   └── favicon.svg           Site favicon
├── .env.example              PUBLIC_API_URL config
├── package.json
├── astro.config.mjs
└── tsconfig.json
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PUBLIC_API_URL` | `http://localhost:5000` | Flask backend URL |

Set in `.env` or `.env.local` for development. Exposed to client via Astro's `envPrefix: 'PUBLIC_'`.

## Pages

| Page | Route | Description |
|------|-------|-------------|
| Landing | `/` | Hero section, features, event preview |
| Dashboard | `/dashboard/` | Streamer status, event configuration (real or mock data) |
| Login | `/login/` | Twitch OAuth redirect to Flask backend |

## API Integration

Dashboard fetches from Flask backend endpoints:

```
GET  /api/csrf-token  → { csrf_token }
GET  /api/me          → { twitch_user_id, display_name, ... }
GET  /api/events      → [{ event_number, action, enabled, ... }]
PUT  /api/events/:id  → { enabled } (with X-CSRF-Token header)
POST /logout          → { success } (with X-CSRF-Token header)
```

**CSRF Protection**: All mutating requests (PUT/POST) include `X-CSRF-Token` header. Token fetched once from `/api/csrf-token` and cached.

**Demo Mode**: If backend is unreachable, dashboard falls back to mock data from `src/data/mock.ts`.

## Components

| Component | Description |
|-----------|-------------|
| `Header` | Sticky navigation with logo and links |
| `Footer` | Site footer with GitHub link |
| `EventCard` | Toggle event enabled/disabled via API |

## Development

```bash
cd site
npm install
npm run dev
# Open http://localhost:4321/chatcontrol/
```

## Build

```bash
npm run build
# Output: site/dist/
```

## Configuration

`astro.config.mjs`:

```javascript
export default defineConfig({
  site: 'https://servirentresubnormales-wq.github.io',
  base: '/chatcontrol',
  output: 'static',
  vite: {
    envPrefix: 'PUBLIC_',
  }
});
```

- `site` — GitHub Pages domain
- `base` — Repository name path prefix
- `output: 'static'` — Pre-rendered HTML
- `vite.envPrefix` — Expose `PUBLIC_*` env vars to client

## Design

- Dark theme (Twitch-inspired)
- Responsive (mobile + desktop)
- Purple (`#9146FF`) primary color
- Inter + JetBrains Mono fonts
- CSS custom properties for theming
