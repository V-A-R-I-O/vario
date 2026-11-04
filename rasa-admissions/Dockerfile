# V.A.R.I.O. — Rasa Admissions role pack (real Rasa 3.6, ADR-006).
# Build from the repository root so the shared channel/tracker store is included:
#   docker build -f rasa-admissions/Dockerfile .
# The same image runs the Rasa server (default CMD) and the action server
# (`run actions --actions actions --port 5055`). The server keeps its models in
# /var/lib/vario/models (mount a volume there); see rasa-shared/docker/rasa-start.sh.
FROM rasa/rasa:3.6.20-full

WORKDIR /app
USER root
COPY rasa-admissions/ /app/
COPY rasa-shared/vario_rasa/ /app/vario_rasa/
COPY rasa-shared/docker/rasa-start.sh /usr/local/bin/vario-rasa-start
RUN chmod +x /usr/local/bin/vario-rasa-start \
    && pip install --no-cache-dir httpx==0.27.0 \
    && rasa train --fixed-model-name admissions-model \
    && mkdir -p /var/lib/vario \
    && chown -R 1001:0 /app /var/lib/vario
ENV PYTHONPATH=/app

EXPOSE 5005 5055
USER 1001
ENTRYPOINT ["vario-rasa-start"]
CMD ["run", "--enable-api", "--port", "5005", "--model", "/var/lib/vario/models", "--credentials", "/app/credentials.yml", "--endpoints", "/app/endpoints.yml"]
