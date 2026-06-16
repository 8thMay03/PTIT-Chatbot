from app.ingestion.chunker import split_text


def test_split_text_returns_ordered_chunks() -> None:
    text = "A" * 100 + "\n\n" + "B" * 100

    chunks = split_text(text, chunk_size=120, chunk_overlap=20)

    assert len(chunks) == 2
    assert chunks[0].index == 0
    assert chunks[1].index == 1
