from app.ingestion import ingestion_pipeline


def main() -> None:
    result = ingestion_pipeline.ingest_documents()
    print(
        f"Ingested {result['documents']} document(s), "
        f"{result['chunks']} chunk(s) into {result['collection']}."
    )


if __name__ == "__main__":
    main()
