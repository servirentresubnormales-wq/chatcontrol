# ChatControl Web Frontend

## Overview

Static frontend for ChatControl built with [Astro](https://astro.build/). Deployed to GitHub Pages.

## Framework

- **Astro 5.x** — Static site generator with minimal JavaScript
- **TypeScript** — Type safety
- **GitHub Pages** — Static hosting

## Structure

```
site/
├── src/
│   ├── pages/
│   │   ├── index.astro       Landing page
│   │   ├── dashboard.astro   Streamer dashboard
│   │   └── login.astro       Twitch login
│   ├── components/
│   │   ├── Header.astro      Navigation header
│   │   ├── Footer.astro      Site footer
│   │   └── EventCard.astro   Event configuration card
│   ├── layouts/
│   │   └── Layout.astro      Base HTML layout
│   └── data/
│       └── mock.ts           Mock data for streamer, events
├── public/
│   └── favicon.svg           Site favicon
├── package.json
├── astro.config.mjs
└── tsconfig.json
```

## Pages

| Page | Route | Description |
|------|-------|-------------|
| Landing | `/` | Hero section, features, event preview |
| Dashboard | `/dashboard/` | Streamer status, event configuration |
| Login | `/login/` | Twitch OAuth button (mock) |

## Components

| Component | Description |
|-----------|-------------|
| `Header` | Sticky navigation with logo and links |
| `Footer` | Site footer with GitHub link |
| `EventCard` | Editable event configuration card |

## Mock Data

All data is mock (`src/data/mock.ts`). Designed to be replaced by API calls:

```typescript
// Future API endpoints
GET  /api/me
GET  /api/settings
PUT  /api/settings
GET  /api/events
PUT  /api/events/:id
GET  /auth/twitch
GET  /auth/twitch/callback
POST /auth/logout
```

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
});
```

- `site` — GitHub Pages domain
- `base` — Repository name path prefix
- `output: 'static'` — Pre-rendered HTML

## Routing

Astro uses file-based routing:

- `src/pages/index.astro` → `/`
- `src/pages/dashboard.astro` → `/dashboard/`
- `src/pages/login.astro` → `/login/`

Trailing slashes are used for directory-style URLs.

## Design

- Dark theme (Twitch-inspired)
- Responsive (mobile + desktop)
- Purple (`#9146FF`) primary color
- Inter + JetBrains Mono fonts
- CSS custom properties for theming

## Future

- Connect to Flask backend for real data
- Implement Twitch OAuth flow
- Add event editing functionality
- Real-time updates via WebSocket
