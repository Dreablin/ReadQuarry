from abc import ABC, abstractmethod
import re


class ChunkingStrategy(ABC):
    @abstractmethod
    def chunk(self, text: str, metadata: dict) -> list[dict]:
        """Split text into metadata-rich chunks."""


class ParagraphChunking(ChunkingStrategy):
    def __init__(self, overlap: int = 1) -> None:
        self.overlap = max(0, overlap)

    def chunk(self, text: str, metadata: dict) -> list[dict]:
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
        chunks: list[dict] = []
        for i, para in enumerate(paragraphs):
            chunk_text = para
            if self.overlap > 0 and i > 0:
                overlap_start = max(0, i - self.overlap)
                overlap_text = "\n\n".join(paragraphs[overlap_start:i])
                chunk_text = f"{overlap_text}\n\n{para}"
            chunks.append(
                {
                    "text": chunk_text,
                    "chunk_index": i,
                    "strategy": "paragraph",
                    **metadata,
                }
            )
        return chunks


class SentenceChunking(ChunkingStrategy):
    def __init__(self, overlap: int = 1) -> None:
        self.overlap = max(0, overlap)

    def chunk(self, text: str, metadata: dict) -> list[dict]:
        # Split on paragraph boundaries first (BUGS.md B05): `\n\n` separates blocks even
        # when the prior block ends without `.`/`!`/`?`/`…`, then split each block on
        # Latin/Cyrillic sentence punctuation followed by whitespace.
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
        sentences: list[str] = []
        for para in paragraphs:
            parts = [s.strip() for s in re.split(r"(?<=[.!?…])\s+", para) if s.strip()]
            sentences.extend(parts)
        chunks: list[dict] = []
        for i, sentence in enumerate(sentences):
            chunk_text = sentence
            if self.overlap > 0 and i > 0:
                overlap_start = max(0, i - self.overlap)
                overlap_text = " ".join(sentences[overlap_start:i])
                chunk_text = f"{overlap_text} {sentence}".strip()
            chunks.append(
                {
                    "text": chunk_text,
                    "chunk_index": i,
                    "strategy": "sentence",
                    **metadata,
                }
            )
        return chunks


class FixedSizeChunking(ChunkingStrategy):
    def __init__(self, chunk_size: int = 256, overlap_ratio: float = 0.15) -> None:
        self.chunk_size = max(1, chunk_size)
        self.overlap_ratio = min(max(overlap_ratio, 0.0), 0.9)

    def chunk(self, text: str, metadata: dict) -> list[dict]:
        words = text.split()
        if not words:
            return []
        overlap_words = int(self.chunk_size * self.overlap_ratio)
        step = max(1, self.chunk_size - overlap_words)

        chunks: list[dict] = []
        chunk_index = 0
        for start in range(0, len(words), step):
            part = words[start : start + self.chunk_size]
            if not part:
                break
            chunks.append(
                {
                    "text": " ".join(part),
                    "chunk_index": chunk_index,
                    "strategy": "fixed-size",
                    **metadata,
                }
            )
            chunk_index += 1
            if start + self.chunk_size >= len(words):
                break
        return chunks


class ChapterAwareRecursiveChunking(ChunkingStrategy):
    def __init__(self, chunk_size: int = 512, overlap: int = 64) -> None:
        self.chunk_size = max(1, chunk_size)
        self.overlap = max(0, overlap)
        self.separators = ["\n\n", "\n", ". ", " "]

    def _split_recursive(self, text: str, separator_index: int = 0) -> list[str]:
        if len(text.split()) <= self.chunk_size or separator_index >= len(self.separators):
            return [text.strip()] if text.strip() else []

        sep = self.separators[separator_index]
        parts = [p.strip() for p in text.split(sep) if p.strip()]
        if len(parts) <= 1:
            return self._split_recursive(text, separator_index + 1)

        out: list[str] = []
        buffer: list[str] = []
        buffer_len = 0
        for part in parts:
            part_len = len(part.split())
            if buffer and buffer_len + part_len > self.chunk_size:
                out.append(sep.join(buffer).strip())
                buffer = [part]
                buffer_len = part_len
            else:
                buffer.append(part)
                buffer_len += part_len
        if buffer:
            out.append(sep.join(buffer).strip())
        return out

    def chunk(self, text: str, metadata: dict) -> list[dict]:
        base_chunks = self._split_recursive(text)
        if not base_chunks:
            return []
        chunks: list[dict] = []
        for i, chunk_text in enumerate(base_chunks):
            with_overlap = chunk_text
            if self.overlap > 0 and i > 0:
                prev_words = base_chunks[i - 1].split()
                overlap_text = " ".join(prev_words[-self.overlap :])
                with_overlap = f"{overlap_text} {chunk_text}".strip()
            chunks.append(
                {
                    "text": with_overlap,
                    "chunk_index": i,
                    "strategy": "chapter-aware-recursive",
                    **metadata,
                }
            )
        return chunks
