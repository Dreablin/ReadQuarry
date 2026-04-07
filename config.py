from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str = "ReadQuarry"
    host: str = "127.0.0.1"
    port: int = 8000
    data_dir: Path = Path("data")
    db_path: Path = Path("data/readquarry.db")


settings = Settings()
