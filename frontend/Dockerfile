# syntax=docker/dockerfile:1
FROM node:20-slim AS builder

WORKDIR /build
COPY package*.json ./
RUN npm ci --omit=dev

# ── runtime ──────────────────────────────────────────────────────────────────
FROM node:20-slim

RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /app
COPY --from=builder /build/node_modules ./node_modules
COPY app.js package.json ./
COPY views ./views

USER app

EXPOSE 3000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD node -e "require('http').get('http://localhost:3000/healthz', r => process.exit(r.statusCode === 200 ? 0 : 1)).on('error', () => process.exit(1))"

CMD ["node", "app.js"]