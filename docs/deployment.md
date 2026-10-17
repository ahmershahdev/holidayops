# Deployment

One production image (`Dockerfile` at the repo root) runs everything: gunicorn serving the API,
the public pages, static files and the built web app, plus the Celery worker and Beat with a
different command. `.github/workflows/deploy.yml` builds it on every push to `main` and pushes
`ghcr.io/ahmershahdev/holidayops:<sha>` and `:latest`.

Target: **Azure Container Apps** at **https://holidayops.ahmershah.dev** (host not final yet; the
image runs on any container host).

## The image

| Command | Role |
|---|---|
| default (`gunicorn config.wsgi …`) | web, port 8000 |
| `celery -A config worker --loglevel=info` | worker |
| `celery -A config beat --loglevel=info --schedule=/tmp/celerybeat-schedule` | Beat, exactly one replica |
| `python manage.py migrate --noinput` | migrations, run once per release before the rollout |

- `/healthz` returns `200 {"status": "ok", …}` when MySQL and Redis answer, else `503`. It is
  answered before host validation and the HTTPS redirect, so probes can call it by IP over HTTP.
- Static files are collected at build time and served by WhiteNoise with hashed names. The web
  app's `index.html` is served for `/`, `/login`, `/signup`, `/invite`, `/unsubscribe` and
  `/app/…`, never cached; its assets come from the site root with long cache lifetimes.
- 324 MB (the old single-stage image was 801 MB): compilers stay in a build stage.

## Run the production image locally

```
docker compose -f docker-compose.prod.yml up --build     # http://localhost:8080
```

It has its own project name, MySQL and Redis, so it runs next to the dev stack.
`DJANGO_HTTPS=false` there turns off the HTTPS redirect, HSTS and secure cookies; never set it in
production.

## Environment

| Variable | Production value |
|---|---|
| `DJANGO_SETTINGS_MODULE` | `config.settings.prod` (the image's default) |
| `DJANGO_SECRET_KEY` | long random string (secret) |
| `DJANGO_ALLOWED_HOSTS` | `holidayops.ahmershah.dev` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://holidayops.ahmershah.dev` |
| `APP_URL` | `https://holidayops.ahmershah.dev` |
| `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD` | the MySQL server (password is a secret) |
| `MYSQL_SSL_MODE` | `REQUIRED` (Azure MySQL rejects plain connections) |
| `MYSQL_SSL_CA` | optional CA bundle path, e.g. `/etc/ssl/certs/ca-certificates.crt`, for `VERIFY_IDENTITY` |
| `REDIS_URL` | `redis://…` (or `rediss://` for TLS) |
| `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL` | an SMTP provider; backend `django.core.mail.backends.smtp.EmailBackend` |
| `PLAN_*`, `API_*_RATE` | optional overrides (`.env.example`) |
| `LOG_LEVEL` | optional, default `INFO` |

## Azure Container Apps

Resources, all in one resource group (e.g. `holidayops-rg`) and region:

| Resource | Notes |
|---|---|
| Container Apps environment | `holidayops-env` |
| Container app `holidayops-web` | external ingress, target port 8000, 1–2 replicas, health probe `/healthz` |
| Container app `holidayops-worker` | no ingress, 1 replica, worker command |
| Container app `holidayops-beat` | no ingress, **exactly 1 replica** (min = max = 1), Beat command |
| Container Apps job `holidayops-migrate` | manual trigger, migrate command |
| Azure Database for MySQL – Flexible Server | 8.x, Burstable tier, database `holidayops`, utf8mb4 |
| Redis | a `redis:7.4-alpine` container app with internal TCP ingress on 6379 is enough here: the queue and caches can be lost on restart (webhook retries live in MySQL). Azure Cache for Redis is the managed alternative. |

Check prices in the Azure pricing calculator against the Azure for Students credit before
creating anything; the Burstable MySQL tier and Container Apps' consumption plan are the cheap
options.

### First-time setup (outline)

```
az group create -n holidayops-rg -l <region>
az containerapp env create -n holidayops-env -g holidayops-rg -l <region>
az mysql flexible-server create -g holidayops-rg -n <server> --tier Burstable --sku-name Standard_B1ms \
  --version 8.0.21 --admin-user <user> --admin-password <secret> --public-access <outbound IPs of the env>
az mysql flexible-server db create -g holidayops-rg -s <server> -d holidayops --charset utf8mb4 \
  --collation utf8mb4_unicode_ci
# then: create the four apps and the job from ghcr.io/ahmershahdev/holidayops:latest with the
# environment above (secrets via `--secrets` and `secretref:`), web with
# `--ingress external --target-port 8000`, beat with `--min-replicas 1 --max-replicas 1`.
```

If the GHCR package stays private, give the apps registry credentials (`--registry-server ghcr.io
--registry-username <github user> --registry-password <PAT with read:packages>`), or make the
package public (it contains no secrets: `.env` is excluded by `.dockerignore`).

### Custom domain: holidayops.ahmershah.dev

1. `az containerapp hostname add -n holidayops-web -g holidayops-rg --hostname holidayops.ahmershah.dev`
   prints the records to create.
2. At the DNS provider of `ahmershah.dev`: a `CNAME` from `holidayops` to the app's
   `<name>.<env-id>.<region>.azurecontainerapps.io` FQDN, and the `TXT` record `asuid.holidayops`
   with the verification ID.
3. `az containerapp hostname bind -n holidayops-web -g holidayops-rg --hostname holidayops.ahmershah.dev
   --environment holidayops-env --validation-method CNAME` issues a free managed certificate.

`.dev` is on the HSTS preload list, so browsers only ever use HTTPS for it; the app also sends
HSTS itself.

### Continuous deployment

`deploy.yml`'s `azure` job runs after the image is pushed, once these are set in the repository:

| Kind | Name | Value |
|---|---|---|
| Variable | `AZURE_DEPLOY` | `true` (until then the job is skipped) |
| Variable | `AZURE_RESOURCE_GROUP` | `holidayops-rg` |
| Secret | `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` | an Entra app registration with a federated credential for this repo's `production` environment (OIDC, no stored password), with Contributor on the resource group |

Each run updates the migrate job's image, runs it and waits for success, then rolls web, worker
and Beat to the new image. Roll back with
`az containerapp update -n <app> -g holidayops-rg --image ghcr.io/ahmershahdev/holidayops:<older sha>`.

## After the first deploy

- Sign up through the site for the first account. `seed_demo` refuses to run without `DEBUG`, on
  purpose, so production never gets a known demo password.
- `python manage.py set_plan <org> pro` to move an org to the pro plan.
- Submit `https://holidayops.ahmershah.dev/sitemap.xml` in Google Search Console.
- Measure Lighthouse on the live public pages (target ≥ 90). Locally, accessibility, best
  practices and SEO score 100 on mobile and desktop; the performance trace fails on Windows
  (`NO_NAVSTART`) for these script-free pages (10 KB HTML + 4.5 KB CSS), so measure it from Linux
  or PageSpeed Insights.
