from __future__ import annotations

import os
from pathlib import Path


class Settings:
    def __init__(self) -> None:
        root = Path(__file__).resolve().parents[2]
        self.db_path = Path(os.getenv("RESERVEHUB_DB_PATH", root / "reservehub.db"))
        self.allowed_origins = [
            item.strip()
            for item in os.getenv("RESERVEHUB_ALLOWED_ORIGINS", "http://127.0.0.1:5179,http://localhost:5179").split(",")
            if item.strip()
        ]
        self.sample_mode = os.getenv("RESERVEHUB_SAMPLE_MODE", "true").lower() == "true"


settings = Settings()
