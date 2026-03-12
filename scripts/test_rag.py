
import os
import sys
from langchain_core.documents import Document

# Add parent directory to sys.path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from vector_stores.chroma import ChromaDBManager
from config import Config

def test_rag():
    print("Initializing ChromaDBManager...")
    db = ChromaDBManager()
    
    collection = "research"
    
    # 1. Add some sample documents
    print(f"Adding sample documents to '{collection}'...")
    docs = [
        Document(
            page_content="The iPhone 15 Pro features a titanium design and an A17 Pro chip.",
            metadata={"title": "iPhone 15 Info", "source": "tech_blog"}
        ),
        Document(
            page_content="The Samsung Galaxy S24 Ultra has a 200MP camera and built-in S Pen.",
            metadata={"title": "S24 Ultra Review", "source": "mobile_insider"}
        ),
        Document(
            page_content="Google Pixel 8 Pro uses the Tensor G3 chip for advanced AI features.",
            metadata={"title": "Pixel 8 Specs", "source": "google_news"}
        ),
        Document(
            page_content="Sony WH-1000XM5 are industry-leading noise-canceling headphones.",
            metadata={"title": "Sony Headphones", "source": "audio_daily"}
        )
    ]
    
    db.add_documents(collection, docs)
    print("Documents added.")
    
    # 2. Test Hybrid Search
    query = "Tell me about mobile phones with high megapixel cameras"
    print(f"\nQuerying: '{query}'")
    results = db.query(collection, query, k=2)
    
    print("\nResults (Hybrid Search + Reranking):")
    for i, doc in enumerate(results):
        print(f"{i+1}. {doc.page_content}")
        print(f"   Metadata: {doc.metadata}\n")

    # 3. Test Keyword Search specifically (BM25)
    query_2 = "titanium chip"
    print(f"Querying for keywords: '{query_2}'")
    results_2 = db.query(collection, query_2, k=1)
    
    print("\nResults:")
    for i, doc in enumerate(results_2):
        print(f"{i+1}. {doc.page_content}")

if __name__ == "__main__":
    try:
        test_rag()
    except Exception as e:
        print(f"Error: {e}")
