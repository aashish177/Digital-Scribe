import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    # API Keys
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # Paths
    BASE_DIR = Path(__file__).parent
    VECTOR_DB_PATH = os.getenv("VECTORDB_PATH", str(BASE_DIR / "data" / "vectordb"))
    OUTPUT_DIR = BASE_DIR / "outputs"

    # Model Settings
    # Writer, researcher and editor need the strong model; the rest are short, simple tasks.
    STRONG_MODEL = os.getenv("STRONG_MODEL", "gpt-6.1-terra")
    FAST_MODEL = os.getenv("FAST_MODEL", "gpt-6-luna")
    STRONG_REASONING_EFFORT = os.getenv("STRONG_REASONING_EFFORT", "low")
    FAST_REASONING_EFFORT = os.getenv("FAST_REASONING_EFFORT", "none")
    AGENT_TIERS = {
        "Planner": "fast",
        "Research": "strong",
        "Writer": "strong",
        "Editor": "strong",
        "SEO": "fast",
        "Translator": "fast",
        "SocialMedia": "fast",
        "ImageGen": "fast",
    }
    # Older models take a temperature; newer ones only accept reasoning_effort.
    TEMPERATURE_MODELS = {"gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini"}
    EMBEDDING_MODEL = "text-embedding-3-small"
    # USD per 1M tokens (input, output), used for cost estimates in the UI.
    MODEL_PRICES = {
        "gpt-6.1-terra": (1.00, 5.00),
        "gpt-6-luna": (0.10, 0.50),
        "gpt-6.1-sol": (2.00, 10.00),
        "gpt-4o": (2.50, 10.00),
        "gpt-4o-mini": (0.15, 0.60),
    }

    # Agent Specifics (Temperatures)
    PLANNER_TEMP = 0.2
    RESEARCHER_TEMP = 0.0
    WRITER_TEMP = 0.7
    EDITOR_TEMP = 0.1
    SEO_TEMP = 0.2
    
    # RAG Settings
    CHUNK_SIZE = 1000
    CHUNK_OVERLAP = 200
    RETRIEVAL_K = 5
    # A query counts as covered when its closest chunk has at least this cosine
    # similarity (text-embedding-3-small). Rerank scores order chunks but don't gate them.
    MIN_QUERY_SIMILARITY = float(os.getenv("MIN_QUERY_SIMILARITY", "0.35"))

    # Uploaded documents
    UPLOAD_MAX_BYTES = 10 * 1024 * 1024
    UPLOAD_MAX_FILES = 5
    UPLOAD_MAX_PAGES = 200
    UPLOAD_MAX_CHUNKS = 2000  # per file, bounds embedding cost
    UPLOAD_PARSE_TIMEOUT = 30.0
    WORKSPACE_TTL_SECONDS = 24 * 3600
    MAX_WORKSPACES = 50
    DOC_PREVIEW_CHARS = 300  # opening text of each upload, shown to the planner
    
    # Logging Configuration
    LOG_DIR = os.getenv("LOG_DIR", "logs")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = os.getenv("LOG_FORMAT", "human")  # "human" or "json"
    
    # Retry Configuration
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_BASE_DELAY = float(os.getenv("RETRY_BASE_DELAY", "1.0"))
    RETRY_MAX_DELAY = float(os.getenv("RETRY_MAX_DELAY", "60.0"))
    REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "120"))
    MAX_WRITER_ATTEMPTS = 2
    MIN_DRAFT_RATIO = 0.25  # of the target word count, after the last attempt

    # API limits
    MAX_JOBS_IN_MEMORY = 200
    JOB_TTL_SECONDS = 24 * 3600  # finished runs (and their retrieved chunks) are forgotten after this
    ALLOWED_ORIGINS = [o for o in os.getenv("ALLOWED_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000").split(",") if o]
    # Webhooks are off unless a host allowlist is configured.
    WEBHOOK_ALLOWED_HOSTS = {h.strip().lower() for h in os.getenv("WEBHOOK_ALLOWED_HOSTS", "").split(",") if h.strip()}

    # Web search (Tavily). The Web source is off unless a key is set.
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
    WEB_RESULTS_PER_QUERY = int(os.getenv("WEB_RESULTS_PER_QUERY", "5"))
    WEB_DAILY_SEARCH_CAP = int(os.getenv("WEB_DAILY_SEARCH_CAP", "100"))  # whole server, resets at local midnight
    WEB_MAX_QUERIES = 5  # per run
    WEB_TIMEOUT = 10.0
    WEB_CACHE_SECONDS = 24 * 3600
    WEB_BLOCKED_DOMAINS = [d.strip().lower() for d in os.getenv("WEB_BLOCKED_DOMAINS", "").split(",") if d.strip()]

    @classmethod
    def tier_for(cls, agent_name: str) -> str:
        return cls.AGENT_TIERS.get(agent_name, "strong")

    @classmethod
    def model_for(cls, agent_name: str) -> str:
        """Per-agent override (e.g. MODEL_EDITOR), else the agent's tier model."""
        override = os.getenv(f"MODEL_{agent_name.upper()}")
        if override:
            return override
        return cls.FAST_MODEL if cls.tier_for(agent_name) == "fast" else cls.STRONG_MODEL

    @classmethod
    def price_for(cls, model: str):
        """Prices for a model name, also matching dated variants like gpt-4o-2024-08-06."""
        if model in cls.MODEL_PRICES:
            return cls.MODEL_PRICES[model]
        matches = [name for name in cls.MODEL_PRICES if model.startswith(name + "-")]
        return cls.MODEL_PRICES[max(matches, key=len)] if matches else None

    @classmethod
    def validate(cls):
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is missing from environment.")
            
# Create output directories if they don't exist
os.makedirs(Config.OUTPUT_DIR, exist_ok=True)
os.makedirs(Config.VECTOR_DB_PATH, exist_ok=True)
os.makedirs(Config.LOG_DIR, exist_ok=True)