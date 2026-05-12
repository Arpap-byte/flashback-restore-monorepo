# ============================================================
# Flashback Restore — Backend Docker
# ============================================================
# Construction :
#   docker build -t flashback-backend .
#
# Exécution :
#   docker run -p 8000:8000 --env-file .env flashback-backend
# ============================================================

FROM python:3.11-slim

# Métadonnées
LABEL org.opencontainers.image.title="Flashback Restore Backend"
LABEL org.opencontainers.image.description="API FastAPI pour la restauration de photos par IA"
LABEL org.opencontainers.image.version="1.0.0"

# Variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=8000

# Répertoire de travail
WORKDIR /app

# Installation des dépendances système
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libjpeg62-turbo-dev \
        libpng-dev \
        libtiff-dev \
        libwebp-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Copie des dépendances Python et installation
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source
COPY app/ ./app/

# Création du répertoire d'uploads
RUN mkdir -p /app/uploads && chmod 777 /app/uploads

# Exposition du port
EXPOSE 8000

# Commande de démarrage
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
