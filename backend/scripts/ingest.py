from app.rag.service import rag_service


def main() -> None:
    result = rag_service.ingest_documents()
    print(
        f"Ingested {result['documents']} document(s), "
        f"{result['chunks']} chunk(s) into {result['collection']}."
    )


if __name__ == "__main__":
    main()
