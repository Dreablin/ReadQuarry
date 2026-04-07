from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str = "ReadQuarry"
    host: str = "127.0.0.1"
    port: int = 8000
    data_dir: Path = Path("data")
    db_path: Path = Path("data/readquarry.db")
    static_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent / "static")


settings = Settings()
