#!/bin/sh
set -eu

storage_dir="/app/backend/storage"
database_file="$storage_dir/ptit_chatbot.db"
chroma_dir="$storage_dir/chroma"

if [ "${PTIT_AUTO_INGEST:-true}" = "true" ] && { [ ! -f "$database_file" ] || [ ! -d "$chroma_dir" ]; }; then
    echo "Knowledge base is empty; ingesting documents..."
    python -m scripts.ingest
fi

exec "$@"

