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
    # We can use a smarter model for planning/writing and faster one for others if needed
    MODEL_NAME = "claude-3-sonnet-20240229"  # Or specific version from spec
    EMBEDDING_MODEL = "text-embedding-3-small"

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

    @classmethod
    def validate(cls):
        if not cls.ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is missing from environment.")
            
# Create output directories if they don't exist
os.makedirs(Config.OUTPUT_DIR, exist_ok=True)
os.makedirs(Config.VECTOR_DB_PATH, exist_ok=True)