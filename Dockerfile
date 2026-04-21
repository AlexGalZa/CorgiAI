# syntax=docker/dockerfile:1.7
# =============================================================================
# Corgi — All-in-One Image
# =============================================================================
# Bundles api (Django), portal (Next.js), and admin (Vite) into one container.
# Nginx on :80 routes:
#   /api/*   → Django gunicorn on 127.0.0.1:8000 (prefix stripped)
#   /ops/*   → Admin SPA static files
#   /*       → Portal Next.js on 127.0.0.1:3000
#   /healthz → nginx-level health check
#
# For a Dokploy deployment: set build type "Dockerfile", build context = repo
# root, and supply DATABASE_* / DJANGO_* / JWT_* env vars at runtime.
#
# Uses BuildKit cache mounts for pnpm + pip + apt so Dokploy rebuilds only
# pay bandwidth for new/changed deps. Dokploy runs BuildKit by default.
# =============================================================================

# ── Node base ──────────────────────────────────────────────────────────────
# node:25-alpine dropped the bundled corepack binary; install pnpm
# globally via npm instead. Pinned to node:22-alpine (LTS) since we
# don't need anything from 25 and 22 is still supported.
FROM node:22-alpine AS node-base
RUN apk add --no-cache libc6-compat
ENV PNPM_HOME="/pnpm" \
    PATH="/pnpm:$PATH"
RUN npm install -g pnpm@9.15.0

# ── Portal (Next.js) build ──────────────────────────────────────────────────
FROM node-base AS portal-builder
WORKDIR /portal
COPY portal/package.json portal/pnpm-lock.yaml .npmrc* ./
RUN --mount=type=cache,id=pnpm,target=/pnpm/store \
    pnpm install --frozen-lockfile --ignore-scripts
COPY portal/ ./
ARG NEXT_PUBLIC_API_URL=
ARG NEXT_PUBLIC_STRIPE_KEY=
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_PUBLIC_STRIPE_KEY=$NEXT_PUBLIC_STRIPE_KEY \
    NEXT_TELEMETRY_DISABLED=1
RUN pnpm run build

# ── Admin (Vite) build ──────────────────────────────────────────────────────
FROM node-base AS admin-builder
WORKDIR /admin
COPY admin/package.json admin/pnpm-lock.yaml .npmrc* ./
RUN --mount=type=cache,id=pnpm,target=/pnpm/store \
    pnpm install --frozen-lockfile --ignore-scripts
COPY admin/ ./
ARG VITE_API_URL=
ARG VITE_SENTRY_DSN=
ARG VITE_SSO_LOGIN_URL=
ENV VITE_API_URL=$VITE_API_URL \
    VITE_SENTRY_DSN=$VITE_SENTRY_DSN \
    VITE_SSO_LOGIN_URL=$VITE_SSO_LOGIN_URL
# Build with base=/ops/ so asset URLs are prefixed correctly behind nginx.
# Invoke tsc + vite directly — `pnpm run build -- --base=...` doesn't forward
# args into the chained script "tsc -b && vite build".
RUN pnpm exec tsc -b && pnpm exec vite build --base=/ops/

# ── API (Python) deps ───────────────────────────────────────────────────────
FROM python:3.14-slim AS api-deps
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
RUN --mount=type=cache,id=apt-api,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,id=apt-api-lists,target=/var/lib/apt/lists,sharing=locked \
    apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
        libpq-dev \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        libcairo2 \
        shared-mime-info \
        fonts-liberation
WORKDIR /api
COPY api/requirements.txt .
RUN --mount=type=cache,id=pip,target=/root/.cache/pip \
    pip install -r requirements.txt supervisor==4.2.5 "setuptools<81"

# ── Runner ──────────────────────────────────────────────────────────────────
FROM python:3.14-slim AS runner
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

# Install runtime system deps + Node.js 20 + nginx + supervisor.
RUN --mount=type=cache,id=apt-runner,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,id=apt-runner-lists,target=/var/lib/apt/lists,sharing=locked \
    apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates curl gnupg wget \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends \
        nodejs \
        nginx \
        postgresql-client \
        libpango-1.0-0 \
        libpangocairo-1.0-0 \
        libgdk-pixbuf-2.0-0 \
        libcairo2 \
        shared-mime-info \
        fonts-liberation \
    && apt-get purge -y gnupg \
    && apt-get autoremove -y

# Bring in installed Python packages from the deps stage
COPY --from=api-deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=api-deps /usr/local/bin /usr/local/bin

# API source
WORKDIR /app/api
COPY api/ ./

# Portal (Next.js standalone output)
WORKDIR /app/portal
COPY --from=portal-builder /portal/public ./public
COPY --from=portal-builder /portal/.next/standalone ./
COPY --from=portal-builder /portal/.next/static ./.next/static

# Admin (static files, served by nginx)
RUN mkdir -p /var/www/ops
COPY --from=admin-builder /admin/dist/ /var/www/ops/

# Bake the commit SHA + build timestamp into /var/www/version.txt so
# /version (via nginx) reports both the commit and when the image was
# produced. Dokploy claims success on pull, but without this we have no
# way to tell "pulled new image" from "kept old container running".
# First line: commit SHA. Second line: ISO-8601 UTC build timestamp.
ARG GIT_SHA=unknown
RUN printf '%s\n%s\n' "$GIT_SHA" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > /var/www/version.txt

# nginx + supervisor + entrypoint
RUN rm -f /etc/nginx/sites-enabled/default /etc/nginx/conf.d/default.conf
COPY deploy/allinone/nginx.conf /etc/nginx/conf.d/corgi.conf
COPY deploy/allinone/supervisord.conf /etc/supervisor/supervisord.conf
COPY deploy/allinone/start-all.sh /usr/local/bin/start-all.sh
# Strip Windows CRLF so the shebang resolves + supervisord config parses.
RUN sed -i 's/\r$//' \
        /usr/local/bin/start-all.sh \
        /etc/supervisor/supervisord.conf \
        /etc/nginx/conf.d/corgi.conf \
    && chmod +x /usr/local/bin/start-all.sh

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/healthz || exit 1

CMD ["/usr/local/bin/start-all.sh"]
