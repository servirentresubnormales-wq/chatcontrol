# GitHub Pages Deployment

## Overview

ChatControl frontend is deployed to GitHub Pages via GitHub Actions.

## Workflow

File: `.github/workflows/deploy-pages.yml`

```
push to main
  ↓
checkout
  ↓
setup node 20
  ↓
npm ci (install dependencies)
  ↓
npm run build (Astro static build)
  ↓
upload-pages-artifact (site/dist/)
  ↓
deploy-pages
```

## Configuration Required

### 1. Enable GitHub Pages

In repository settings:

1. Go to **Settings** → **Pages**
2. Under **Source**, select **GitHub Actions**
3. Save

### 2. Repository Name

The repository must be named `chatcontrol` for the URL to work:

```
https://servirentresubnormales-wq.github.io/chatcontrol/
```

### 3. Base Path

`astro.config.mjs` must match the repository name:

```javascript
export default defineConfig({
  site: 'https://servirentresubnormales-wq.github.io',
  base: '/chatcontrol',
});
```

## URL

After deployment:

```
https://servirentresubnormales-wq.github.io/chatcontrol/
```

Pages with trailing slashes:

- `/chatcontrol/` — Landing page
- `/chatcontrol/dashboard/` — Dashboard
- `/chatcontrol/login/` — Login

## Triggering Deployment

Deployment triggers automatically on:

- Push to `main` branch
- Manual trigger via `workflow_dispatch`

## Troubleshooting

### 404 on subpages

Astro uses directory-style URLs. Ensure:
- Pages are accessed with trailing slash: `/dashboard/` not `/dashboard`
- `build.format: 'directory'` in `astro.config.mjs`

### Build fails

Check Node.js version (must be 20+) and that `package-lock.json` exists.

### Styling broken

Verify `base: '/chatcontrol'` in `astro.config.mjs` matches the repo name.

### Actions not running

Ensure Pages source is set to "GitHub Actions" in repository Settings → Pages.

## Manual Deployment

```bash
cd site
npm ci
npm run build
# Upload site/dist/ contents to gh-pages branch
```

## CI Workflow

File: `.github/workflows/ci.yml`

Runs on push/PR to main:

| Job | Command | Description |
|-----|---------|-------------|
| Bridge | `python -m pytest -v` | Python tests (447) |
| Core | `./gradlew clean build` | Java build + tests (130) |
| Frontend | `npm ci && npm run build` | Astro build |
