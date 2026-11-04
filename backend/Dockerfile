# V.A.R.I.O. — Backend (FastAPI Gateway)
FROM python:3.11-slim

WORKDIR /app

# Install dependencies first for better layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .
RUN chmod +x docker-entrypoint.sh

EXPOSE 8000

# Migrates and seeds before serving (see docker-entrypoint.sh).
CMD ["./docker-entrypoint.sh"]
