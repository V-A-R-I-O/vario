#!/bin/sh
set -eu

# The role-pack service runs from its persistent volume so models produced by
# POST /model/train survive container recreation. Seed the volume from the
# image's trained model only on first startup; never overwrite a trained model.
if [ "${1:-}" = "run" ] && [ "${2:-}" != "actions" ]; then
    model_dir="/var/lib/vario/models"
    mkdir -p "$model_dir"
    if ! ls "$model_dir"/*.tar.gz >/dev/null 2>&1; then
        cp /app/models/*.tar.gz "$model_dir/"
    fi
    cd /var/lib/vario
    exec rasa run \
        --model "$model_dir" \
        --enable-api \
        --port 5006 \
        --credentials /app/credentials.yml \
        --endpoints /app/endpoints.yml
fi

# The same image is used by the separate Rasa SDK action server.
exec rasa "$@"
