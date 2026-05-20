"""Central configuration, driven by environment variables (.env supported).

Everything that will differ between the dummy phase and the real-data phase
lives here, so the swap is a config change, not a code change.
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root if present.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

# --- Paths -----------------------------------------------------------------
DATA_DIR = Path(os.getenv("NLSQL_DATA_DIR", PROJECT_ROOT / "app" / "data" / "store"))
CHDB_PATH = str(DATA_DIR / "chdb")          # persistent embedded-ClickHouse store
AUDIT_DB_PATH = str(DATA_DIR / "audit.db")  # SQLite audit log
INDEX_PATH = str(DATA_DIR / "vector_index.npz")   # RAG vector index

# --- Pipeline knobs --------------------------------------------------------
ENABLE_PROMPT_ENHANCER = os.getenv("ENABLE_PROMPT_ENHANCER", "true").lower() == "true"
ENABLE_RESULT_FORMATTER = os.getenv("ENABLE_RESULT_FORMATTER", "true").lower() == "true"
MAX_QUERIES_PER_DAY = int(os.getenv("MAX_QUERIES_PER_DAY", "200"))

# --- Database --------------------------------------------------------------
# DB_BACKEND = "chdb"           -> embedded ClickHouse (dummy phase, no server)
# DB_BACKEND = "clickhouse_http" -> real ClickHouse HTTP endpoint (real-data phase)
DB_BACKEND = os.getenv("DB_BACKEND", "chdb")
DB_NAME = os.getenv("DB_NAME", "turtlemint")

# Used only when DB_BACKEND == "clickhouse_http" (the production path).
CLICKHOUSE_URL = os.getenv("CLICKHOUSE_URL", "")          # e.g. https://clickhouse.internal:8443
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_USER", "nlsql_ro")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_PASSWORD", "")

# --- LLM (Google Gemini via its OpenAI-compatible endpoint) ----------------
LLM_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai")
LLM_MODEL = os.getenv("GEMINI_MODEL") or os.getenv("LLM_MODEL", "gemini-2.5-flash")
LLM_TIMEOUT_S = float(os.getenv("LLM_TIMEOUT_S", "60"))
LLM_MAX_RETRIES = int(os.getenv("LLM_MAX_RETRIES", "3"))
EMBED_MODEL = os.getenv("EMBED_MODEL", "gemini-embedding-001")
# Models tried (in order) if the primary is overloaded/rate-limited.
LLM_FALLBACK_MODELS = [
    m.strip() for m in os.getenv(
        "LLM_FALLBACK_MODELS", "gemini-2.5-flash-lite,gemini-3.1-flash-lite"
    ).split(",") if m.strip()
]

# --- Guardrails ------------------------------------------------------------
SQL_DIALECT = os.getenv("SQL_DIALECT", "clickhouse")
DEFAULT_ROW_LIMIT = int(os.getenv("DEFAULT_ROW_LIMIT", "1000"))
QUERY_TIMEOUT_S = int(os.getenv("QUERY_TIMEOUT_S", "30"))

# --- Backend ---------------------------------------------------------------
BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "chdb").mkdir(parents=True, exist_ok=True)
