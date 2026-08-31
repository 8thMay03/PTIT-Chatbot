#!/bin/sh
set -eu

echo "Applying database migrations..."
python -m alembic upgrade head


storage_dir="/app/backend/storage"
chroma_dir="$storage_dir/chroma"

if [ "${PTIT_AUTO_INGEST:-true}" = "true" ] && [ ! -d "$chroma_dir" ]; then
    echo "Knowledge base is empty; ingesting documents..."
    python -m scripts.ingest
fi

exec "$@"


