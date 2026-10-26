import pytest

from scripts import ingest


@pytest.mark.parametrize(
    ("argv", "method", "result", "message"),
    [
        ([], "ingest_documents", {"documents": 2, "chunks": 9, "collection": "c"}, "Ingested 2 document(s), 9 chunk(s)"),
        (["--stage", "parse"], "parse_documents", {"documents": 2}, "Parsed 2 document(s)"),
        (
            ["--stage", "chunk"],
            "chunk_documents",
            {"documents": 2, "chunks": 9, "skipped": 1, "collection": "c"},
            "skipped 1 without a stored parse",
        ),
    ],
)
def test_stage_selects_pipeline_step(monkeypatch, capsys, argv, method, result, message) -> None:
    calls = []
    for name in ("ingest_documents", "parse_documents", "chunk_documents"):
        monkeypatch.setattr(
            ingest.ingestion_pipeline, name, lambda name=name: calls.append(name) or result
        )

    ingest.main(argv)

    assert calls == [method]
    assert message in capsys.readouterr().out


def test_unknown_stage_is_rejected() -> None:
    with pytest.raises(SystemExit):
        ingest.main(["--stage", "embed"])
