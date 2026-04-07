from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from src.db.database import Base
from src.models.book import Book, Paragraph
from src.models.chat import ChatMessage, ChatSession
from src.models.chunk import Chunk
from src.models.settings import AppSettings


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(dbapi_connection, _connection_record):  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True)()


def test_book_related_entities_crud() -> None:
    session = make_session()

    book = Book(
        title="Book",
        author="Author",
        file_name="book.epub",
        file_hash="hash-1",
        chunking_strategy="paragraph",
        total_paragraphs=1,
        total_chunks=1,
    )
    session.add(book)
    session.commit()

    paragraph = Paragraph(book_id=book.id, chapter_title="Ch 1", chapter_index=1, paragraph_index=0, text="Para")
    chunk = Chunk(book_id=book.id, chapter_title="Ch 1", chunk_index=0, strategy="paragraph", text="Chunk")
    chat_session = ChatSession(book_id=book.id, title="Session A")
    session.add_all([paragraph, chunk, chat_session])
    session.commit()

    message = ChatMessage(session_id=chat_session.id, role="user", content="Hello", referenced_chunks='[1]')
    session.add(message)
    session.commit()

    assert session.query(Book).count() == 1
    assert session.query(Paragraph).count() == 1
    assert session.query(Chunk).count() == 1
    assert session.query(ChatSession).count() == 1
    assert session.query(ChatMessage).count() == 1


def test_cascade_delete_book_removes_related_rows() -> None:
    session = make_session()

    book = Book(
        title="Book",
        author=None,
        file_name="book.epub",
        file_hash="hash-2",
        chunking_strategy="paragraph",
        total_paragraphs=1,
        total_chunks=1,
    )
    session.add(book)
    session.commit()

    chat_session = ChatSession(book_id=book.id, title="Session B")
    session.add(chat_session)
    session.commit()

    session.add_all(
        [
            Paragraph(book_id=book.id, chapter_title=None, chapter_index=None, paragraph_index=0, text="Para"),
            Chunk(book_id=book.id, chapter_title=None, chunk_index=0, strategy="paragraph", text="Chunk"),
            ChatMessage(session_id=chat_session.id, role="assistant", content="Hi", referenced_chunks=None),
        ]
    )
    session.commit()

    session.delete(book)
    session.commit()

    assert session.query(Book).count() == 0
    assert session.query(Paragraph).count() == 0
    assert session.query(Chunk).count() == 0
    assert session.query(ChatSession).count() == 0
    assert session.query(ChatMessage).count() == 0


def test_unique_constraint_on_book_file_hash() -> None:
    session = make_session()
    session.add(
        Book(
            title="A",
            author=None,
            file_name="a.epub",
            file_hash="dup",
            chunking_strategy="paragraph",
            total_paragraphs=0,
            total_chunks=0,
        )
    )
    session.commit()

    session.add(
        Book(
            title="B",
            author=None,
            file_name="b.epub",
            file_hash="dup",
            chunking_strategy="paragraph",
            total_paragraphs=0,
            total_chunks=0,
        )
    )

    try:
        session.commit()
        raised = False
    except Exception:  # sqlite integrity error type can vary by driver path
        session.rollback()
        raised = True

    assert raised is True


def test_app_settings_crud() -> None:
    session = make_session()

    setting = AppSettings(key="llm_mode", value="openai")
    session.add(setting)
    session.commit()

    saved = session.get(AppSettings, "llm_mode")
    assert saved is not None
    assert saved.value == "openai"

    saved.value = "ollama"
    session.commit()
    updated = session.get(AppSettings, "llm_mode")
    assert updated is not None
    assert updated.value == "ollama"

    session.delete(updated)
    session.commit()
    assert session.get(AppSettings, "llm_mode") is None
