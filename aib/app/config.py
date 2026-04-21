"""
Configuration loader — reads .env and validates required keys.
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

# ── Required ────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
if not ANTHROPIC_API_KEY:
    print("ERROR: Missing required environment variable ANTHROPIC_API_KEY", file=sys.stderr)
    sys.exit(1)

# ── Database ────────────────────────────────────────────────────────────
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://{user}:{password}@{host}:{port}/{name}".format(
        user=os.getenv("DB_USER", "aib"),
        password=os.getenv("DB_PASSWORD", "aib_password"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
        name=os.getenv("DB_NAME", "aib"),
    ),
)

# ── Server ──────────────────────────────────────────────────────────────
PORT: int = int(os.getenv("PORT", "7860"))
DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

# ── File uploads ────────────────────────────────────────────────────────
UPLOADS_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10 MB
ALLOWED_MIME_TYPES: dict[str, str] = {
    "image/jpeg": "image",
    "image/jpg": "image",
    "image/png": "image",
    "application/pdf": "pdf",
}
