# Deep Buddy

**Deep Buddy** is a tactical-class RMM product skin in the Bhudi Online monorepo.

Inspired by **Tactical RMM** workflows (client → site → agent), powered by the **Bhudi** native agent and runtime API.

## URLs

| Path | Purpose |
|------|---------|
| `/deep-buddy` | Marketing website |
| `/deep-buddy/console` | RMM dashboard |
| `/deep-buddy/console/clients` | Live client / site tree |
| `/deep-buddy/console/agents` | Agent fleet |

## API

| Endpoint | Purpose |
|----------|---------|
| `GET /api/v1/deep-buddy/tree` | Client → site → agent tree |
| `GET /api/v1/deep-buddy/status` | Product / fleet summary |

## Deploy

See **[DEPLOY.md](./DEPLOY.md)** for live DB tree, dedicated Vercel domain, and Tactical script mapping.

## Brand

- **Deep Buddy** — product
- **Cyber Bastion** — parent
- **Bhudi Online** — full platform sibling
