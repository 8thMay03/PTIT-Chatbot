from app.ingestion.chunker import Chunk, split_text
from app.ingestion.loaders import SourceDocument, load_documents

__all__ = [
    "Chunk",
    "IngestionPipeline",
    "SourceDocument",
    "ingestion_pipeline",
    "load_documents",
    "split_text",
]


def __getattr__(name: str):
    if name in {"IngestionPipeline", "ingestion_pipeline"}:
        from app.ingestion.pipeline import IngestionPipeline, ingestion_pipeline

        return {
            "IngestionPipeline": IngestionPipeline,
            "ingestion_pipeline": ingestion_pipeline,
        }[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
