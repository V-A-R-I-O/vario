# V.A.R.I.O. — Rasa HR role pack (real Rasa 3.6, ADR-006).
# Build from the repository root so the shared channel/tracker store is included:
#   docker build -f rasa-hr/Dockerfile .
# The same image runs the Rasa server (default CMD) and the action server
# (`run actions --actions actions --port 5055`).
FROM rasa/rasa:3.6.20-full

WORKDIR /app
USER root
COPY rasa-hr/ /app/
COPY rasa-shared/vario_rasa/ /app/vario_rasa/
RUN pip install --no-cache-dir httpx==0.27.0 \
    && rasa train --fixed-model-name hr-model \
    && chown -R 1001:0 /app
ENV PYTHONPATH=/app

EXPOSE 5005 5055
USER 1001
CMD ["run", "--enable-api", "--port", "5005", "--model", "models", "--credentials", "credentials.yml", "--endpoints", "endpoints.yml"]
