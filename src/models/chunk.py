from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.database import Base


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True)
    chapter_title: Mapped[str | None] = mapped_column(String, nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    strategy: Mapped[str] = mapped_column(String, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    paragraph_ids: Mapped[str | None] = mapped_column(Text, nullable=True)

    book: Mapped["Book"] = relationship(back_populates="chunks")


from src.models.book import Book  # noqa: E402  # circular import typing only
