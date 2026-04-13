# Stage 1: Build the React Dashboard
FROM node:20-alpine AS frontend-builder
WORKDIR /web
# Copy package files
COPY tlcm-web/package*.json ./
RUN npm install
# Copy React source
COPY tlcm-web/ ./
RUN npm run build

# Stage 2: Build the Python API Backend
FROM python:3.11-slim
WORKDIR /app

# System dependencies for ChromaDB and SQLite
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY core/ core/
COPY server/ server/
COPY integrations/ integrations/
COPY tlcm_client.py .
COPY pyproject.toml .

# Install as a package
RUN pip install -e .

# Copy the compiled React dashboard from Stage 1 into the place the backend expects it
COPY --from=frontend-builder /web/dist /app/tlcm-web/dist

# Expose the Universal API and Dashboard port
EXPOSE 8000

# Set environment
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Data storage directory (can be mounted via Volume)
ENV TLCM_DATA_DIR=/app/data

# Run the Uvicorn server seamlessly
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
