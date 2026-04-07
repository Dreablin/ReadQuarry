from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile


router = APIRouter(prefix="/api/books", tags=["books"])

_BOOKS: dict[int, dict] = {}
_NEXT_ID = 1


@router.post("/upload")
async def upload_book(file: UploadFile = File(...), chunking_strategy: str = Form("paragraph")) -> dict:
    global _NEXT_ID
    allowed_strategies = {"paragraph", "sentence", "fixed-size", "chapter-aware-recursive"}
    if chunking_strategy not in allowed_strategies:
        raise HTTPException(status_code=400, detail="Unsupported chunking strategy")
    if not file.filename or not file.filename.lower().endswith(".epub"):
        raise HTTPException(status_code=400, detail="Only EPUB files are supported")

    book_id = _NEXT_ID
    _NEXT_ID += 1

    # Save upload to local runtime data folder.
    data_dir = Path("data/uploads")
    data_dir.mkdir(parents=True, exist_ok=True)
    destination = data_dir / f"{book_id}_{file.filename}"
    content = await file.read()
    destination.write_bytes(content)

    record = {
        "id": book_id,
        "title": Path(file.filename).stem,
        "author": None,
        "file_name": file.filename,
        "chunking_strategy": chunking_strategy,
        "upload_date": datetime.utcnow().isoformat(),
    }
    _BOOKS[book_id] = record
    return record


@router.get("")
def list_books() -> list[dict]:
    return list(_BOOKS.values())


@router.get("/{book_id}")
def get_book(book_id: int) -> dict:
    record = _BOOKS.get(book_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return record


@router.delete("/{book_id}")
def delete_book(book_id: int) -> dict:
    if book_id not in _BOOKS:
        raise HTTPException(status_code=404, detail="Book not found")
    _BOOKS.pop(book_id)
    return {"status": "deleted", "id": book_id}
