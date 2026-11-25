import os
import re
import threading
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever
from langchain_community.document_compressors.flashrank_rerank import FlashrankRerank
from langchain_classic.embeddings import CacheBackedEmbeddings
from langchain_classic.storage import LocalFileStore
from config import Config

# Clients, BM25 indexes and the reranker are expensive to build, so every
# ChromaDBManager in the process shares one set per database path.
_shared: Dict[str, Dict[str, Any]] = {}
_lock = threading.Lock()
RERANK_POOL = 20
WORKSPACE_PATTERN = re.compile(r"^ws_[0-9a-f]{32}$")


def workspace_collection(workspace_id: str) -> str:
    return f"ws_{workspace_id}"


def _resources(path: str) -> Dict[str, Any]:
    with _lock:
        if path not in _shared:
            os.makedirs(path, exist_ok=True)
            cache_dir = os.path.join(path, "embeddings_cache")
            os.makedirs(cache_dir, exist_ok=True)
            raw_embeddings = OpenAIEmbeddings(model=Config.EMBEDDING_MODEL, api_key=Config.OPENAI_API_KEY)
            embeddings = CacheBackedEmbeddings.from_bytes_store(
                raw_embeddings,
                LocalFileStore(cache_dir),
                namespace=Config.EMBEDDING_MODEL,
            )
            _shared[path] = {
                "embeddings": embeddings,
                # Uploads skip the disk cache so deleting a workspace leaves nothing behind.
                "uncached_embeddings": raw_embeddings,
                "client": chromadb.PersistentClient(path=str(path)),
                "stores": {},
                "bm25": {},
                "reranker": None,
            }
        return _shared[path]


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
        shared = _resources(self.persist_path)
        self.embedding_function = shared["embeddings"]
        self.uncached_embedding_function = shared["uncached_embeddings"]
        self.client = shared["client"]
        self.vector_stores = shared["stores"]
        self._bm25_retrievers = shared["bm25"]
        self._shared = shared
        
    def get_vector_store(self, collection_name: str) -> Chroma:
        """
        Get or create a LangChain Chroma vector store wrapper for a specific collection.
        """
        if collection_name in self.COLLECTIONS:
            real_collection_name = self.COLLECTIONS[collection_name]
            embedding_function = self.embedding_function
        elif WORKSPACE_PATTERN.match(collection_name):
            real_collection_name = collection_name
            embedding_function = self.uncached_embedding_function
        else:
            raise ValueError(f"Unknown collection type: {collection_name}. Valid types: {list(self.COLLECTIONS.keys())}")
        
        if collection_name not in self.vector_stores:
            with _lock:
                if collection_name not in self.vector_stores:
                    self.vector_stores[collection_name] = Chroma(
                        client=self.client,
                        collection_name=real_collection_name,
                        embedding_function=embedding_function,
                    )
            
        return self.vector_stores[collection_name]

    def add_documents(self, collection_name: str, documents: List[Document]) -> List[str]:
        """
        Add documents to a specific collection.
        """
        store = self.get_vector_store(collection_name)
        ids = store.add_documents(documents)
        self._bm25_retrievers.pop(collection_name, None)
        return ids

    def delete_documents(self, collection_name: str, doc_id: str) -> None:
        """Remove every chunk of one uploaded document."""
        store = self.get_vector_store(collection_name)
        store.delete(where={"doc_id": doc_id})
        self._bm25_retrievers.pop(collection_name, None)

    def drop_collection(self, collection_name: str) -> None:
        """Delete a workspace collection and its cached indexes."""
        if not WORKSPACE_PATTERN.match(collection_name):
            raise ValueError("Only workspace collections can be dropped")
        with _lock:
            self.vector_stores.pop(collection_name, None)
            self._bm25_retrievers.pop(collection_name, None)
        try:
            self.client.delete_collection(collection_name)
        except Exception:
            pass  # already gone

    def get_bm25_retriever(self, collection_name: str) -> Optional[BM25Retriever]:
        """Get or create the BM25Retriever for a specific collection."""
        if collection_name not in self._bm25_retrievers:
            store = self.get_vector_store(collection_name)
            all_docs = store.get()
            docs, metadatas = all_docs.get("documents", []), all_docs.get("metadatas", [])
            if not docs:
                return None
            langchain_docs = [Document(page_content=doc, metadata=meta or {}) for doc, meta in zip(docs, metadatas)]
            retriever = BM25Retriever.from_documents(langchain_docs, k=RERANK_POOL // 2)
            with _lock:
                self._bm25_retrievers.setdefault(collection_name, retriever)
            
        return self._bm25_retrievers[collection_name]
        
    def get_reranker(self):
        with _lock:
            if not self._shared["reranker"]:
                self._shared["reranker"] = FlashrankRerank(top_n=RERANK_POOL)
        return self._shared["reranker"]

    def query(self, collection_name: str, query_text: str, k: int = 4, filter: Optional[Dict] = None,
              min_similarity: Optional[float] = None) -> List[Document]:
        """
        Query a specific collection using Advanced Hybrid Search (Vector + BM25) and FlashRank Reranking.
        Returns nothing when the closest chunk's cosine similarity is below min_similarity.
        """
        store = self.get_vector_store(collection_name)
        
        # Fetch dense docs. Chroma's default l2 distance on unit vectors is 2 - 2*cos.
        dense = store.similarity_search_with_score(query_text, k=k*2, filter=filter)
        if min_similarity is not None:
            best = max((1 - distance / 2 for _, distance in dense), default=-1.0)
            if best < min_similarity:
                return []
        dense_docs = [doc for doc, _ in dense]
        all_docs = {doc.page_content: doc for doc in dense_docs}
        
        # Sparse retrieval (BM25 Keyword Search)
        sparse_retriever = self.get_bm25_retriever(collection_name)
        if sparse_retriever:
            sparse_docs = sparse_retriever.invoke(query_text)
            for doc in sparse_docs:
                if doc.page_content not in all_docs:
                    all_docs[doc.page_content] = doc
                    
        combined_docs = list(all_docs.values())
        
        if not combined_docs:
            return []
            
        reranker = self.get_reranker()
        reranked_docs = reranker.compress_documents(combined_docs, query_text)
        # FlashRank returns numpy floats, which the graph checkpointer cannot serialize.
        for doc in reranked_docs:
            if "relevance_score" in doc.metadata:
                doc.metadata["relevance_score"] = float(doc.metadata["relevance_score"])
        
        return reranked_docs[:k]
        
    def query_multireturn(self, collection_name: str, query_text: str, k: int = 4,
                          min_similarity: Optional[float] = None) -> List[Dict]:
        """
        Query and return a list of dictionaries with content and metadata.
        Useful for passing raw data to agents.
        """
        docs = self.query(collection_name, query_text, k, min_similarity=min_similarity)
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
