#!/usr/bin/env sh
set -eu

CHECKPOINT_PATH="${BIONUCLEI_CHECKPOINT:-/opt/models/bionuclei.pt}"
if [ ! -f "$CHECKPOINT_PATH" ] && [ -n "${BIONUCLEI_CHECKPOINT_URL:-}" ]; then
    echo "bionuclei: fetching checkpoint" >&2
    mkdir -p "$(dirname "$CHECKPOINT_PATH")"
    python - "$CHECKPOINT_PATH" "$BIONUCLEI_CHECKPOINT_URL" "${BIONUCLEI_CHECKPOINT_SHA256:-}" <<'PY'
import hashlib
import sys
import urllib.request
from pathlib import Path

destination = Path(sys.argv[1])
url = sys.argv[2]
expected = sys.argv[3]
tmp = destination.with_suffix(destination.suffix + ".download")
urllib.request.urlretrieve(url, tmp)
actual = hashlib.sha256(tmp.read_bytes()).hexdigest()
if expected and actual != expected:
    tmp.unlink(missing_ok=True)
    raise SystemExit(f"FATAL checkpoint hash mismatch: expected={expected} actual={actual}
tmp.replace(destination)
print(f"checkpoint_sha256={actual}")
PY
fi

if [ ! -f "$CHECKPOINT_PATH" ]; then
    echo "bionuclei: FATAL checkpoint unavailable; configure BIONUCLEI_CHECKPOINT_URL" >&2
    exit 1
fi

exec uvicorn webapp.community_app:app --host 0.0.0.0 --port "${PORT:-8000}"
