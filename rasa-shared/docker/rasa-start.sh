#!/bin/sh
# Entrypoint for the VARIO Rasa images: the Rasa server and the action server.
#
# The server runs from /var/lib/vario (a volume), so models trained through
# POST /model/train (admin retraining) survive container recreation. The model
# baked into the image is copied in when the volume has none, or when the image
# is newer: a rebuild with new training data wins over older retrained models.
set -eu

if [ "${1:-}" = "run" ] && [ "${2:-}" != "actions" ]; then
    store=/var/lib/vario/models
    baked=$(ls /app/models/*.tar.gz 2>/dev/null | head -n 1)
    if [ -z "$baked" ]; then
        echo "No trained model in this image; rebuild it with: docker compose build" >&2
        exit 1
    fi
    mkdir -p "$store"
    newest=$(ls -t "$store"/*.tar.gz 2>/dev/null | head -n 1)
    if [ -z "$newest" ] || [ "$baked" -nt "$newest" ]; then
        cp -p "$baked" "$store/"
    fi
    # Retrained models are saved to ./models, relative to the working directory.
    cd /var/lib/vario
    # Protects Rasa's HTTP API (training, model loading). Rasa treats an empty
    # --auth-token as a real token, so pass it only when one is configured.
    if [ -n "${RASA_AUTH_TOKEN:-}" ]; then
        set -- "$@" --auth-token "$RASA_AUTH_TOKEN"
    fi
fi

exec rasa "$@"
