# syntax=docker/dockerfile:1.7
# Car Checker web app.
#   dev      -> Vite dev server, source mounted from the host (docker compose)
#   runtime  -> static build served by unprivileged nginx, /api proxied to the backend

ARG NODE_VERSION=22

FROM node:${NODE_VERSION}-alpine AS dev
WORKDIR /app
USER node
EXPOSE 5173
CMD ["sh", "-c", "npm install --no-audit --no-fund && npm run dev"]

FROM node:${NODE_VERSION}-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.29-alpine AS runtime
ENV API_UPSTREAM=http://api:8000
COPY nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
