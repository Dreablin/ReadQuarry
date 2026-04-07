from src.db.database import Base
from src.models.book import Book, Paragraph
from src.models.chat import ChatMessage, ChatSession
from src.models.chunk import Chunk
from src.models.settings import AppSettings


def test_all_required_tables_are_declared() -> None:
    expected = {
        "books",
        "paragraphs",
        "chunks",
        "chat_sessions",
        "chat_messages",
        "app_settings",
    }
    assert expected.issubset(set(Base.metadata.tables.keys()))


def test_models_have_expected_tablenames() -> None:
    assert Book.__tablename__ == "books"
    assert Paragraph.__tablename__ == "paragraphs"
    assert Chunk.__tablename__ == "chunks"
    assert ChatSession.__tablename__ == "chat_sessions"
    assert ChatMessage.__tablename__ == "chat_messages"
    assert AppSettings.__tablename__ == "app_settings"
