# syntax=docker/dockerfile:1
FROM python:3.11-slim

# HF_HOME keeps Docling's layout/table models (downloaded on first use) on the storage volume.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/app/backend/storage/.cache/huggingface

WORKDIR /app/backend

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /app/backend/storage \
    && chown appuser:appuser /app /app/backend /app/backend/storage

# Dependencies first, from pyproject.toml alone: this heavy layer (torch, Docling) is
# reused until dependencies change, so code or data edits never reinstall it. A stub
# package lets pip resolve the project; the code runs from the working directory.
# The pip cache mount keeps downloaded wheels between builds without adding them to the image.
COPY backend/pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/pip \
    mkdir app && touch app/__init__.py \
    && pip install --upgrade pip \
    # CPU-only torch wheels keep the image far smaller than the default CUDA build.
    && pip install --extra-index-url https://download.pytorch.org/whl/cpu ".[docling,llamaparse]" \
    && pip uninstall -y ptit-chatbot-backend \
    && rm -rf app build *.egg-info

COPY backend/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN sed -i 's/\r$//' /usr/local/bin/docker-entrypoint.sh \
    && chmod +x /usr/local/bin/docker-entrypoint.sh

# Most frequently edited last. docker-compose also mounts these for live reload.
COPY --chown=appuser:appuser data /app/data
COPY --chown=appuser:appuser backend/alembic.ini ./alembic.ini
COPY --chown=appuser:appuser backend/alembic ./alembic
COPY --chown=appuser:appuser backend/scripts ./scripts
COPY --chown=appuser:appuser backend/app ./app

USER appuser

EXPOSE 8000

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
