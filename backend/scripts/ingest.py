import argparse

from app.ingestion import ingestion_pipeline


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Nạp tài liệu trong DOCUMENTS_PATH vào kho tri thức.")
    parser.add_argument(
        "--stage",
        choices=("all", "parse", "chunk"),
        default="all",
        help=(
            "all: parse rồi chia đoạn toàn bộ kho (mặc định); "
            "parse: chỉ parse và lưu Markdown, giữ nguyên các đoạn hiện có; "
            "chunk: chia đoạn lại từ Markdown đã lưu, không parse lại."
        ),
    )
    args = parser.parse_args(argv)

    if args.stage == "parse":
        result = ingestion_pipeline.parse_documents()
        print(f"Parsed {result['documents']} document(s); run --stage chunk to index them.")
    elif args.stage == "chunk":
        result = ingestion_pipeline.chunk_documents()
        print(
            f"Chunked {result['documents']} document(s), "
            f"{result['chunks']} chunk(s) into {result['collection']}; "
            f"skipped {result['skipped']} without a stored parse."
        )
    else:
        result = ingestion_pipeline.ingest_documents()
        print(
            f"Ingested {result['documents']} document(s), "
            f"{result['chunks']} chunk(s) into {result['collection']}."
        )


if __name__ == "__main__":
    main()
