from src.api.books import router as books_router
from src.api.search import router as search_router
from src.api.settings import router as settings_router

__all__ = ["books_router", "search_router", "settings_router"]
