import os
import sys
from pathlib import Path

os.environ["RESERVEHUB_DB_PATH"] = str(Path(__file__).parent / "test_reservehub.db")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
