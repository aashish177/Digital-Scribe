import os
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever
from langchain_community.document_compressors.flashrank_rerank import FlashrankRerank
from langchain.embeddings import CacheBackedEmbeddings
from langchain.storage import LocalFileStore
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
        
        # Initialize embedding function with persistent caching
        # This prevents redundant calls to OpenAI during testing and development
        underlying_embeddings = OpenAIEmbeddings(
            model=Config.EMBEDDING_MODEL,
            api_key=Config.OPENAI_API_KEY
        )
        
        # Setup local file store for embeddings cache
        cache_dir = os.path.join(self.persist_path, "embeddings_cache")
        os.makedirs(cache_dir, exist_ok=True)
        store = LocalFileStore(cache_dir)
        
        self.embedding_function = CacheBackedEmbeddings.from_bytes_store(
            underlying_embeddings,
            store,
            namespace=Config.EMBEDDING_MODEL
        )
        
        # Initialize client
        self.client = chromadb.PersistentClient(path=str(self.persist_path))
        
        # Initialize stores lazy-loaded or upfront
        self.vector_stores = {}
        
        # Cache for BM25 Retrievers per collection
        self._bm25_retrievers = {}
        
        # Lazy-loaded reranker
        self._reranker = None
        
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

    def get_bm25_retriever(self, collection_name: str) -> Optional[BM25Retriever]:
        """Get or create the BM25Retriever for a specific collection."""
        if collection_name not in self._bm25_retrievers:
            store = self.get_vector_store(collection_name)
            # Retrieve all documents to build the BM25 index
            all_docs = store.get()
            
            docs, metadatas = all_docs.get("documents", []), all_docs.get("metadatas", [])
            
            if not docs:
                return None
                
            langchain_docs = [Document(page_content=doc, metadata=meta or {}) for doc, meta in zip(docs, metadatas)]
            self._bm25_retrievers[collection_name] = BM25Retriever.from_documents(langchain_docs)
            
        return self._bm25_retrievers[collection_name]
        
    def get_reranker(self):
        if not self._reranker:
            self._reranker = FlashrankRerank(top_n=4)
        return self._reranker

    def query(self, collection_name: str, query_text: str, k: int = 4, filter: Optional[Dict] = None) -> List[Document]:
        """
        Query a specific collection using Advanced Hybrid Search (Vector + BM25) and FlashRank Reranking.
        """
        store = self.get_vector_store(collection_name)
        
        # Fetch dense docs
        dense_docs = store.similarity_search(query_text, k=k*2, filter=filter)
        all_docs = {doc.page_content: doc for doc in dense_docs}
        
        # Sparse retrieval (BM25 Keyword Search)
        sparse_retriever = self.get_bm25_retriever(collection_name)
        if sparse_retriever:
            sparse_retriever.k = k * 2
            sparse_docs = sparse_retriever.invoke(query_text)
            for doc in sparse_docs:
                if doc.page_content not in all_docs:
                    all_docs[doc.page_content] = doc
                    
        combined_docs = list(all_docs.values())
        
        if not combined_docs:
            return []
            
        reranker = self.get_reranker()
        reranked_docs = reranker.compress_documents(combined_docs, query_text)
        
        return reranked_docs[:k]
        
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
