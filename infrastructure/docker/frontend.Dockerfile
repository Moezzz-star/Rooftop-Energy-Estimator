# =============================================================================
# frontend.Dockerfile — React + Vite SPA.
#   target `dev`  : node:20-slim, Vite dev server on :5173 (hot reload).
#   target `prod` : build with node, serve static assets via nginx on :8080.
# Both run as non-root (`node` / `nginx`). VITE_API_URL is injected at build
# (prod) or runtime (dev).
# =============================================================================

# --- Base with dependencies --------------------------------------------------
FROM node:20-slim AS deps
WORKDIR /app
# package manifests first for layer caching (authored by frontend engineer).
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci

# --- Development target (Vite dev server) ------------------------------------
FROM node:20-slim AS dev
WORKDIR /app
ENV NODE_ENV=development
COPY --from=deps /app/node_modules ./node_modules
COPY frontend/ ./
USER node
EXPOSE 5173
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD wget -qO- http://localhost:5173/ >/dev/null 2>&1 || exit 1
# --host exposes the dev server outside the container network namespace.
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]

# --- Production build stage --------------------------------------------------
FROM node:20-slim AS build
WORKDIR /app
ARG VITE_API_URL=/api
ENV VITE_API_URL=${VITE_API_URL}
COPY --from=deps /app/node_modules ./node_modules
COPY frontend/ ./
RUN npm run build

# --- Production runtime (nginx, non-root, :8080) -----------------------------
FROM nginx:1.27-alpine AS prod
# Custom config: listen on 8080 with writable temp/pid paths so nginx can run
# as the unprivileged `nginx` user.
COPY infrastructure/docker/nginx.conf /etc/nginx/nginx.conf
COPY --from=build /app/dist /usr/share/nginx/html
RUN touch /tmp/nginx.pid \
    && chown -R nginx:nginx /tmp/nginx.pid /var/cache/nginx /usr/share/nginx/html
USER nginx
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost:8080/ >/dev/null 2>&1 || exit 1
CMD ["nginx", "-g", "daemon off;"]
