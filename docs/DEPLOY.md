## Deploy Runbook

### Terraform
```bash
cd terraform
terraform apply -auto-approve
```

### Verify instance is ready
```bash
aws ssm start-session --target $(terraform output -raw instance_id)
cloud-init status  # wait until: status: done
exit
```

### GitHub Actions
- Update `ROLE_ARN_APP` in the GitHub `prod` environment: `terraform output -raw github_actions_role_arn`
- Push to `main` (or manually trigger **Build & Deploy Streamlit App Container**)

### Cloudflare
- Update A record to `terraform output -raw elastic_ip`
- Set SSL to **Flexible**

### SSM (Certbot)
```bash
aws ssm start-session --target $(terraform output -raw instance_id)
sudo certbot --nginx -d spaceweatherdashboard.com --non-interactive --agree-tos -m <email>
```

### Cloudflare
- Set SSL to **Full**

---

## Web (React on Cloudflare Pages) + API (FastAPI on Render)

The React frontend (`web/`) deploys to Cloudflare Pages; the FastAPI caching
layer (`api/`) deploys to Render, proxied through the same Cloudflare zone
at `api.<domain>`. Two settings live outside this repo (Pages project env
vars, Render env vars / dashboard) and both must be kept in sync whenever a
custom domain is added or changed:

- **`VITE_API_BASE_URL`** (Cloudflare Pages → Settings → Environment
  variables): build-time var baked into the bundle by `web/src/app_utils.ts`.
  Must be set for every environment that serves traffic (Production *and*
  Preview) - a build made before the var existed, or made against the wrong
  environment, bakes in the `http://localhost:8000` fallback instead.
- **`CORS_ALLOW_ORIGINS`** (Render → the API service → Environment):
  `api/main.py` defaults this to `*` only when the var is unset. Once it's
  set, `CORSMiddleware` matches the browser's `Origin` header by exact
  string - scheme, host, and (implicit) port, no wildcards, no path, no
  trailing slash. It must list **every** hostname the frontend is actually
  served from, comma-separated, e.g.:
  ```
  CORS_ALLOW_ORIGINS=https://spaceweatherdashboard.com,https://www.spaceweatherdashboard.com,https://<project>.pages.dev
  ```
  Missing one variant (commonly the `www.` form, or the redirect target
  Cloudflare Pages sends apex traffic to) is invisible from the `pages.dev`
  URL, since that origin only needs its own entry to work - it only shows up
  once someone lands on the missing custom-domain variant.

### Troubleshooting: "Could not reach the API" on the custom domain but not on `*.pages.dev`

This message (`web/src/app_utils.ts`) fires only when the browser's
`fetch()` itself throws - a DNS failure, TLS failure, or a CORS
preflight/response rejection - never for a 4xx/5xx from the API (those get
their own message, e.g. the rate limiter's `429 Rate limit exceeded`). Since
the request target (`https://api.<domain>`) is identical regardless of which
frontend origin loaded the page, an asymmetry between `pages.dev` and the
custom domain almost always traces back to one of:

1. **`CORS_ALLOW_ORIGINS` missing the exact custom-domain origin(s)** - see
   above. Most common cause of *intermittent* failures specifically: if both
   the apex and `www.` domains are configured in Cloudflare Pages and only
   one is allow-listed, requests fail 100% of the time from the missing
   variant and succeed 100% of the time from the other, which reads as
   "sometimes works" across visits. Check the Origin the browser is actually
   sending (Network tab) against the exact value of `CORS_ALLOW_ORIGINS` on
   Render.
2. **Cloudflare SSL/TLS mode isn't Full or Full (strict)** for the zone (or
   a per-hostname Configuration Rule override) for `api.<domain>`. Render
   terminates valid HTTPS itself; **Flexible** mode (used earlier in this
   runbook for the old EC2/Nginx box, before Certbot) causes Cloudflare to
   speak plain HTTP to the origin, which can loop or reset intermittently
   depending on edge PoP. Check Cloudflare dashboard → SSL/TLS → Overview.
3. **Render custom domain not fully verified** for the API service - an
   in-progress or dropped verification can serve Render's default response
   for that hostname from some edge caches and the real app from others
   until it fully propagates. Check Render → the API service → Settings →
   Custom Domains.
