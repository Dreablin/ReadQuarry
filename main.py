from fastapi import FastAPI
import uvicorn

from config import settings


app = FastAPI(title=settings.app_name)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=False)
