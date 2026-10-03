import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./reports.db")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
AI_MODEL = os.getenv("AI_MODEL", "gemini-3.5-flash")
FRONTEND_ORIGINS = [
    o.strip()
    for o in os.getenv("FRONTEND_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
    if o.strip()
]
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "uploads"))
MAX_PHOTO_BYTES = 2 * 1024 * 1024  # 2 MB
