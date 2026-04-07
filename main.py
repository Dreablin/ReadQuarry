from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config import settings
from src.api.books import router as books_router
from src.api.chat import router as chat_router
from src.api.search import router as search_router
from src.api.settings import router as settings_router
from src.db.database import Base, engine


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    import src.models  # noqa: F401  # register all models with SQLAlchemy metadata

    settings.data_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, lifespan=_lifespan)
app.include_router(books_router)
app.include_router(search_router)
app.include_router(settings_router)
app.include_router(chat_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


app.mount(
    "/",
    StaticFiles(directory=str(settings.static_dir), html=True),
    name="spa",
)


if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=False)
