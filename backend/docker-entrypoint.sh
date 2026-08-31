#!/bin/sh
set -eu

echo "Applying database migrations..."
python -m alembic upgrade head

if [ "${PTIT_AUTO_INGEST:-true}" = "true" ]; then
    python -c "
from app.db.session import SessionLocal
from app.db.models import Chunk
from sqlalchemy import select
with SessionLocal() as session:
    has_chunks = session.scalar(select(Chunk.id).where(Chunk.embedding.is_not(None)).limit(1)) is not None
    exit(0 if has_chunks else 1)
" || {
        echo "Knowledge base is empty; ingesting documents into PostgreSQL pgvector..."
        python -m scripts.ingest
    }
fi

exec "$@"
