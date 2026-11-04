FROM rasa/rasa:3.6.20-full
WORKDIR /app
USER root
COPY rasa-it/ /app/
COPY rasa-shared/vario_rasa/ /app/vario_rasa/
COPY rasa-shared/docker/rasa-start.sh /usr/local/bin/vario-rasa-start
RUN chmod +x /usr/local/bin/vario-rasa-start \
    && pip install --no-cache-dir httpx==0.27.0 \
    && rasa train --fixed-model-name it-model \
    && mkdir -p /var/lib/vario \
    && chown -R 1001:0 /app /var/lib/vario
ENV PYTHONPATH=/app
EXPOSE 5006 5055
USER 1001
ENTRYPOINT ["vario-rasa-start"]
CMD ["run", "--enable-api", "--port", "5006", "--model", "/var/lib/vario/models", "--credentials", "/app/credentials.yml", "--endpoints", "/app/endpoints.yml"]
