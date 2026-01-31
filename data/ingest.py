import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from vector_stores.chroma import ChromaDBManager

def create_mock_data():
    """Generates mock data for all collections"""
    
    # 1. Research Documents
    research_docs = [
        Document(
            page_content="""
            Green Tea Health Benefits:
            Green tea is rich in polyphenols, which are natural compounds that have health benefits, such as reducing inflammation and helping to fight cancer.
            Green tea contains a catechin called epigallocatechin-3-gallate (EGCG). Catechins are natural antioxidants that help prevent cell damage and provide other benefits.
            Studies show that green tea may improve brain function. The key active ingredient is caffeine. It also contains the amino acid L-theanine, which can cross the blood-brain barrier.
            Green tea may burn fat and boost metabolic rate. In one study of 10 healthy men, taking green tea extract increased the number of calories burned by 4%.
            """,
            metadata={"source": "healthline_mock.txt", "title": "Green Tea Benefits", "topic": "health"}
        ),
        Document(
            page_content="""
            Coffee vs Tea:
            While both coffee and tea provide caffeine, tea generally provides a smoother buzz due to L-theanine.
            Coffee typically has more caffeine per cup (95mg vs 35-50mg for green tea).
            Both are loaded with antioxidants, but they are different types.
            """,
            metadata={"source": "beverage_comparison.txt", "title": "Coffee vs Tea", "topic": "health"}
        )
    ]
    
    # 2. Writing Samples (Templates/High-quality content)
    writing_samples = [
        Document(
            page_content="""
            Title: The Ultimate Guide to Indoor Plants
            
            Indoor plants are more than just decoration; they breathed life into a home. In this comprehensive guide, we will explore...
            
            Key Takeaway: Start with snake plants if you are a beginner.
            """,
            metadata={"style": "guide", "tone": "informative"}
        ),
        Document(
            page_content="""
            Top 10 Tech Trends of 2025
            
            #1. AI Agents everywhere.
            #2. Quantum Computing leaps.
            ...
            """,
            metadata={"style": "listicle", "tone": "exciting"}
        )
    ]
    
    # 3. Style Guide
    style_guide = [
        Document(
            page_content="""
            Brand Voice:
            - Professional but accessible.
            - Use active voice.
            - Avoid jargon where possible.
            - Oxford comma is mandatory.
            """,
            metadata={"section": "voice"}
        ),
         Document(
             page_content="""
             Formatting:
             - Use H2 for main sections.
             - Bullet points for readability.
             - Short paragraphs (max 3-4 sentences).
             """,
             metadata={"section": "formatting"}
         )
    ]
    
    # 4. SEO Data
    seo_data = [
        Document(
            page_content="""
            Keyword: "green tea benefits"
            Volume: 100k
            Difficulty: Medium
            Related: "weight loss tea", "matcha health benefits"
            """,
            metadata={"keyword": "green tea benefits"}
        )
    ]
    
    return {
        "research": research_docs,
        "writing": writing_samples,
        "style": style_guide,
        "seo": seo_data
    }

def ingest_data():
    """Ingests mock data into ChromaDB"""
    print("Initializing ChromaDB Manager...")
    try:
        db_manager = ChromaDBManager()
    except Exception as e:
        print(f"Error initializing DB: {e}")
        return

    data = create_mock_data()
    
    # Text splitter for chunking
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    
    for collection_type, documents in data.items():
        print(f"Processing collection: {collection_type}...")
        
        # Split documents
        chunked_docs = splitter.split_documents(documents)
        print(f"  - Created {len(chunked_docs)} chunks from {len(documents)} docs.")
        
        # Add to DB
        try:
            db_manager.add_documents(collection_type, chunked_docs)
            print("  - Successfully stored in ChromaDB.")
        except Exception as e:
            print(f"  - Error adding documents: {e}")
            
    print("\nIngestion Complete!")

if __name__ == "__main__":
    ingest_data()
