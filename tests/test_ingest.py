from data.ingest import load_source_documents


def test_load_source_documents(tmp_path):
    topic_dir = tmp_path / "sleep"
    topic_dir.mkdir()
    (topic_dir / "melatonin.md").write_text(
        '---\n{"title": "Melatonin", "url": "https://en.wikipedia.org/wiki/Melatonin", "revision": 1, "license": "CC BY-SA 4.0"}\n---\nMelatonin is a hormone.\n'
    )

    docs = load_source_documents(tmp_path)

    assert len(docs) == 1
    assert docs[0].page_content == "Melatonin is a hormone.\n"
    assert docs[0].metadata == {
        "source": "https://en.wikipedia.org/wiki/Melatonin",
        "title": "Melatonin",
        "topic": "sleep",
        "revision": 1,
    }


def test_bundled_sources_load():
    docs = load_source_documents()

    assert len(docs) == 20
    assert {d.metadata["topic"] for d in docs} == {
        "tea-and-coffee", "renewable-energy", "sleep", "space-exploration"
    }
