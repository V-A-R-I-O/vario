FROM rasa/rasa:3.6.20-full
WORKDIR /app
USER root
COPY rasa-it/ /app/
COPY rasa-shared/vario_rasa/ /app/vario_rasa/
RUN chmod +x /app/entrypoint.sh \
    && pip install --no-cache-dir httpx==0.27.0 \
    && rasa train --fixed-model-name it-model \
    && chown -R 1001:0 /app
ENV PYTHONPATH=/app
EXPOSE 5006 5055
USER 1001
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["run", "--enable-api", "--port", "5006", "--credentials", "credentials.yml", "--endpoints", "endpoints.yml"]
