from src.core.chunking import (
    ChapterAwareRecursiveChunking,
    FixedSizeChunking,
    ParagraphChunking,
    SentenceChunking,
)


def test_paragraph_chunk_count_and_overlap() -> None:
    text = "P1.\n\nP2.\n\nP3."
    chunks = ParagraphChunking(overlap=1).chunk(text, metadata={"book_id": 1, "chapter": "C1"})
    assert len(chunks) == 3
    assert chunks[0]["text"] == "P1."
    assert chunks[1]["text"] == "P1.\n\nP2."
    assert chunks[2]["text"] == "P2.\n\nP3."
    assert all(c["chapter"] == "C1" for c in chunks)


def test_sentence_chunk_count_and_overlap() -> None:
    text = "One. Two! Three?"
    chunks = SentenceChunking(overlap=1).chunk(text, metadata={"book_id": 1})
    assert len(chunks) == 3
    assert chunks[0]["text"] == "One."
    assert chunks[1]["text"] == "One. Two!"
    assert chunks[2]["text"] == "Two! Three?"


def test_sentence_chunking_splits_russian_punctuation() -> None:
    """B05: Russian uses the same . ! ? and Unicode ellipsis as sentence boundaries."""
    text = "Первое предложение. Второе! Третье?"
    chunks = SentenceChunking(overlap=0).chunk(text, metadata={"book_id": 1})
    assert len(chunks) == 3
    assert chunks[0]["text"] == "Первое предложение."
    assert chunks[1]["text"] == "Второе!"
    assert chunks[2]["text"] == "Третье?"


def test_sentence_chunking_splits_on_unicode_ellipsis() -> None:
    text = "Начало… Конец."
    chunks = SentenceChunking(overlap=0).chunk(text, metadata={"book_id": 1})
    assert len(chunks) == 2
    assert chunks[0]["text"] == "Начало…"
    assert chunks[1]["text"] == "Конец."


def test_sentence_chunking_b05_paragraph_boundary_without_terminal_punct() -> None:
    """B05: \\n\\n is a block boundary even when the prior block has no . ! ? …"""
    text = "No ending punctuation here\n\nSecond paragraph starts."
    chunks = SentenceChunking(overlap=0).chunk(text, metadata={"book_id": 1})
    assert len(chunks) == 2
    assert chunks[0]["text"] == "No ending punctuation here"
    assert chunks[1]["text"] == "Second paragraph starts."


def test_sentence_chunking_b05_multi_paragraph_then_sentences() -> None:
    """B05: split paragraphs first, then sentences inside each."""
    text = (
        "Alpha starts. Alpha ends.\n\n"
        "Beta only.\n\n"
        "Gamma middle. Gamma last."
    )
    chunks = SentenceChunking(overlap=0).chunk(text, metadata={"book_id": 1})
    assert len(chunks) == 5
    assert chunks[0]["text"] == "Alpha starts."
    assert chunks[1]["text"] == "Alpha ends."
    assert chunks[2]["text"] == "Beta only."
    assert chunks[3]["text"] == "Gamma middle."
    assert chunks[4]["text"] == "Gamma last."


def test_fixed_size_chunking_overlap_and_boundaries() -> None:
    text = "one two three four five six seven eight"
    chunks = FixedSizeChunking(chunk_size=4, overlap_ratio=0.25).chunk(text, metadata={"book_id": 1})
    assert len(chunks) == 3
    assert chunks[0]["text"] == "one two three four"
    assert chunks[1]["text"] == "four five six seven"
    assert chunks[2]["text"] == "seven eight"


def test_recursive_chunking_keeps_metadata_and_strategy() -> None:
    text = (
        "Paragraph one has enough words to trigger splitting and preserve chapter metadata.\n\n"
        "Paragraph two also has many words to continue the split behavior and ensure chunk generation."
    )
    chunks = ChapterAwareRecursiveChunking(chunk_size=10, overlap=2).chunk(
        text,
        metadata={"book_id": 1, "chapter": "Intro"},
    )
    assert len(chunks) >= 2
    assert all(c["strategy"] == "chapter-aware-recursive" for c in chunks)
    assert all(c["chapter"] == "Intro" for c in chunks)
    assert all(c["text"].strip() for c in chunks)
