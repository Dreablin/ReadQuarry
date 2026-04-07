from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.database import Base


class Book(Base):
    __tablename__ = "books"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    author: Mapped[str | None] = mapped_column(String, nullable=True)
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    file_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    chunking_strategy: Mapped[str] = mapped_column(String, nullable=False)
    total_paragraphs: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_chunks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    upload_date: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    paragraphs: Mapped[list["Paragraph"]] = relationship(back_populates="book", cascade="all, delete-orphan")
    chunks: Mapped[list["Chunk"]] = relationship(back_populates="book", cascade="all, delete-orphan")
    chat_sessions: Mapped[list["ChatSession"]] = relationship(back_populates="book", cascade="all, delete-orphan")


class Paragraph(Base):
    __tablename__ = "paragraphs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    book_id: Mapped[int] = mapped_column(ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True)
    chapter_title: Mapped[str | None] = mapped_column(String, nullable=True)
    chapter_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    paragraph_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    book: Mapped["Book"] = relationship(back_populates="paragraphs")


from src.models.chat import ChatSession  # noqa: E402  # circular import typing only
from src.models.chunk import Chunk  # noqa: E402  # circular import typing only
