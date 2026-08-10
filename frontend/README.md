# Bhudi frontend

Production site: **https://bhudi.online**

## Domain (Vercel)

1. Open **Vercel → your project → Settings → Domains**
2. Add:
   - `bhudi.online`
   - `www.bhudi.online` (redirect to apex)
3. At your DNS host (registrar):
   - **A** record for `@` → `76.76.21.21`, **or** follow Vercel’s exact records shown in the UI
   - **CNAME** for `www` → `cname.vercel-dns.com`
4. Project **Environment variables**:
   - `NEXT_PUBLIC_SITE_URL=https://bhudi.online`
   - `NEXT_PUBLIC_API_URL=<Railway API URL>`
5. Redeploy. Visitors should only see **bhudi.online** in the address bar.

Optional: under Domains, set **bhudi.online** as the primary domain so production links prefer it over `*.vercel.app`.

## Local

```bash
npm install
npm run dev
```
