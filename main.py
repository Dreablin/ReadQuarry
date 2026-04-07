from fastapi import FastAPI
import uvicorn

from config import settings
from src.api.books import router as books_router
from src.api.search import router as search_router
from src.api.settings import router as settings_router


app = FastAPI(title=settings.app_name)
app.include_router(books_router)
app.include_router(search_router)
app.include_router(settings_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=False)
