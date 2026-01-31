import os
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from config import Config

class ChromaDBManager:
    """
    Manages interactions with ChromaDB for the content generation pipeline.
    Handles multiple collections for research, writing samples, style guides, and SEO.
    """
    
    COLLECTIONS = {
        "research": "research_docs",
        "writing": "writing_samples",
        "style": "style_guide",
        "seo": "seo_data"
    }
    
    def __init__(self, persistent_path: Optional[str] = None):
        """
        Initialize the ChromaDB manager.
        
        Args:
            persistent_path: Path to store the vector database. Defaults to config value.
        """
        self.persist_path = persistent_path or Config.VECTOR_DB_PATH
        
        # Ensure directory exists
        os.makedirs(self.persist_path, exist_ok=True)
        
        # Initialize embedding function
        # Using OpenAI embeddings as specified in spec
        self.embedding_function = OpenAIEmbeddings(
            model=Config.EMBEDDING_MODEL,
            api_key=Config.OPENAI_API_KEY
        )
        
        # Initialize client
        self.client = chromadb.PersistentClient(path=str(self.persist_path))
        
        # Initialize stores lazy-loaded or upfront
        self.vector_stores = {}
        
    def get_vector_store(self, collection_name: str) -> Chroma:
        """
        Get or create a LangChain Chroma vector store wrapper for a specific collection.
        """
        if collection_name not in self.COLLECTIONS:
            raise ValueError(f"Unknown collection type: {collection_name}. Valid types: {list(self.COLLECTIONS.keys())}")
            
        real_collection_name = self.COLLECTIONS[collection_name]
        
        if collection_name not in self.vector_stores:
            self.vector_stores[collection_name] = Chroma(
                client=self.client,
                collection_name=real_collection_name,
                embedding_function=self.embedding_function,
            )
            
        return self.vector_stores[collection_name]

    def add_documents(self, collection_name: str, documents: List[Document]) -> List[str]:
        """
        Add documents to a specific collection.
        """
        store = self.get_vector_store(collection_name)
        return store.add_documents(documents)

    def query(self, collection_name: str, query_text: str, k: int = 4, filter: Optional[Dict] = None) -> List[Document]:
        """
        Query a specific collection for relevant documents.
        """
        store = self.get_vector_store(collection_name)
        
        # simple similarity search
        # We can enhance this with MMR (Maximum Marginal Relevance) if needed
        docs = store.similarity_search(query_text, k=k, filter=filter)
        return docs
        
    def query_multireturn(self, collection_name: str, query_text: str, k: int = 4) -> List[Dict]:
        """
        Query and return a list of dictionaries with content and metadata.
        Useful for passing raw data to agents.
        """
        docs = self.query(collection_name, query_text, k)
        results = []
        for doc in docs:
            results.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "source": doc.metadata.get("source", "unknown")
            })
        return results

    def list_collections(self) -> List[str]:
        """List all available collections in the DB."""
        return [c.name for c in self.client.list_collections()]
