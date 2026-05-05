# ============================================================
# Flashback Restore — Landing Page Docker
# Image Next.js pour la page d'atterrissage
# ============================================================
# Construction :
#   docker build -t flashback-landing .
# ============================================================

# --- Étape 1 : Build ---
FROM node:22-alpine AS builder

WORKDIR /app

# Copie des fichiers de dépendances
COPY package.json package-lock.json ./

# Installation des dépendances
RUN npm ci --omit=dev

# Copie du code source
COPY . .

# Build Next.js
RUN npm run build

# --- Étape 2 : Runtime ---
FROM node:22-alpine AS runner

WORKDIR /app

# Métadonnées
LABEL org.opencontainers.image.title="Flashback Restore Landing"
LABEL org.opencontainers.image.description="Page d'atterrissage Next.js pour Flashback Restore"
LABEL org.opencontainers.image.version="1.0.0"

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Copie des fichiers nécessaires pour l'exécution
COPY --from=builder /app/package.json ./
COPY --from=builder /app/package-lock.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/next.config.ts ./

# Exposition
EXPOSE 3000

# Démarrage
CMD ["npx", "next", "start", "--port", "3000"]
