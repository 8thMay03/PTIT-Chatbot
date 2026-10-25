"""RAG-15: thay index bằng đúng các tài liệu chỉ định (mỗi file một parser) để đo eval.

Chạy từ backend/:
    python ../documents/rag-eval/rag-15/experiments/reingest_documents.py <path>... [--parser NAME]

Thay load_documents bằng đúng các tài liệu này (cách làm của RAG-05/RAG-06), lưu
metadata.parser theo parser đã dùng; --parser áp cho mọi file, bỏ trống = mặc định
theo đuôi file. Dùng cả để khôi phục index sau khi đo. Không đụng file nguồn.
"""

import argparse
import sys

sys.path.insert(0, ".")

from pathlib import Path

from app.ingestion import pipeline
from app.ingestion.loaders import SourceDocument
from app.parsers import get_parser_name, read_document_text


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", type=Path, nargs="+")
    parser.add_argument("--parser", dest="parser_name", default=None)
    args = parser.parse_args()

    documents = []
    # Absolute paths keep source_path (and so document IDs) identical to app ingestion.
    for path in (path.resolve() for path in args.paths):
        name = get_parser_name(path, args.parser_name)
        text = read_document_text(path, parser_name=name)
        print({"path": path.name, "parser": name, "chars": len(text)})
        documents.append(SourceDocument(path=path, text=text, parser_name=name))

    pipeline.load_documents = lambda _data_dir, **_kwargs: documents
    print(pipeline.ingestion_pipeline.ingest_documents())


if __name__ == "__main__":
    main()
