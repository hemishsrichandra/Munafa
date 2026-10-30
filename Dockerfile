# Multi-stage Dockerfile for Munafa / Paytm Business Partner
# Stage 1: Build React 19 Frontend and PWA Assets using Debian glibc
FROM node:22-bookworm-slim AS frontend-builder
WORKDIR /app

# Copy all project files needed for build
COPY package*.json ./
COPY capacitor.config.json ./
COPY scripts/ ./scripts/
COPY frontend/ ./frontend/

# Clean install dependencies across workspaces and build PWA
RUN npm ci
RUN npm run build

# Stage 2: Python FastAPI Backend with PostgreSQL Driver
FROM python:3.12-slim
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    APP_ENV=production \
    DATABASE_SCHEMA=public

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend application code & migrations
COPY backend/ ./backend/
COPY alembic.ini ./

# Copy built frontend static distribution from builder stage
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Expose port (default 8000)
EXPOSE 8000

# Entrypoint script to run migrations and start server
CMD ["sh", "-c", "alembic upgrade head && uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
