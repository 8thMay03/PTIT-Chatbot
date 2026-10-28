from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings
from app.core.config_store import load_persisted_config
from app.db import init_db


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Áp cấu hình admin đã lưu trong DB lên trên .env. Chạy ở lifespan (không phải lúc
    # import) để test dùng TestClient(app) không đọc cấu hình từ DB dev.
    load_persisted_config()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="PTIT RAG Chatbot API", version="0.1.0", lifespan=lifespan)
    init_db()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="/api")
    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="localhost",
        port=8000,
        reload=True,
        log_level="info",
    )
