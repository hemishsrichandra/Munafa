"""Load ONLY this starter's private environment file; never discover Munafa's .env."""

from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")
