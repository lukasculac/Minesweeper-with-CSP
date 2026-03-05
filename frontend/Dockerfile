# ── Stage 1: build ────────────────────────────────────────────────────────────
FROM node:20-slim AS build

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

# WebSocket URL is injected at build time.
# When running via docker-compose, the browser connects to the host machine
# which reverse-proxies /ws to the backend container.
ARG VITE_WS_URL=ws://localhost:8000/ws
ENV VITE_WS_URL=$VITE_WS_URL

RUN npm run build

# ── Stage 2: serve ─────────────────────────────────────────────────────────────
FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
