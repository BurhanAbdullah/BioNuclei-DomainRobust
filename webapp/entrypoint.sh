#!/usr/bin/env sh
set -eu
CHECKPOINT_PATH="${BIONUCLEI_CHECKPOINT:-/opt/models/bionuclei.pt}"
if [ ! -f "$CHECKPOINT_PATH" ] && [ -n "${BIONUCLEI_CHECKPOINT_URL:-}" ]; then
    echo "bionuclei: fetching checkpoint" >&2
    mkdir -p "$(dirname "$CHECKPOINT_PATH")"
    tmp_path="${CHECKPOINT_PATH}.download"
    curl -fSL --retry 3 -o "$tmp_path" "$BIONUCLEI_CHECKPOINT_URL"
    if [ -n "${BIONUCLEI_CHECKPOINT_SHA256:-}" ]; then
        actual_hash="$(sha256sum "$tmp_path" | cut -d' ' -f1)"
        if [ "$actual_hash" != "$BIONUCLEI_CHECKPOINT_SHA256" ]; then
            echo "bionuclei: FATAL checkpoint hash mismatch" >&2
            rm -f "$tmp_path"
            exit 1
        fi
    else
        echo "bionuclei: WARNING checkpoint hash not configured" >&2
    fi
    mv "$tmp_path" "$CHECKPOINT_PATH"
fi
exec uvicorn webapp.app:app --host 0.0.0.0 --port "${PORT:-8000}"
