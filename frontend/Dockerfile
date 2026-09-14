# syntax=docker/dockerfile:1.7

FROM node:22.23.2-alpine3.24 AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN --mount=type=cache,id=kuriboh-npm,target=/root/.npm,sharing=locked npm ci

COPY . .

ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN npm run build

FROM caddy:2.11.4-alpine

COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv

EXPOSE 80 443 443/udp
