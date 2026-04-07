from src.core.chunking import (
    ChapterAwareRecursiveChunking,
    FixedSizeChunking,
    ParagraphChunking,
    SentenceChunking,
)


def test_paragraph_chunking_generates_chunks() -> None:
    strategy = ParagraphChunking(overlap=1)
    chunks = strategy.chunk(
        "A para.\n\nB para.\n\nC para.",
        metadata={"book_id": 1, "chapter": "Intro"},
    )
    assert len(chunks) >= 3
    assert chunks[0]["strategy"] == "paragraph"


def test_sentence_chunking_generates_chunks() -> None:
    strategy = SentenceChunking(overlap=1)
    chunks = strategy.chunk("One. Two! Three?", metadata={"book_id": 1})
    assert len(chunks) >= 3
    assert chunks[0]["strategy"] == "sentence"


def test_fixed_size_chunking_respects_chunk_size() -> None:
    strategy = FixedSizeChunking(chunk_size=4, overlap_ratio=0.25)
    chunks = strategy.chunk("one two three four five six seven", metadata={"book_id": 1})
    assert len(chunks) >= 2
    for chunk in chunks:
        assert len(chunk["text"].split()) <= 4
        assert chunk["strategy"] == "fixed-size"


def test_chapter_recursive_chunking_generates_chunks() -> None:
    strategy = ChapterAwareRecursiveChunking(chunk_size=20, overlap=5)
    text = "Para one has many words and sentences.\n\nPara two also has enough words to split and recurse."
    chunks = strategy.chunk(text, metadata={"book_id": 1, "chapter": "C1"})
    assert len(chunks) >= 1
    assert chunks[0]["strategy"] == "chapter-aware-recursive"
