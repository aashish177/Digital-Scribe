import os
import sys
import glob

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from vector_stores.chroma import ChromaDBManager

def get_files(directory_path, extensions):
    files = []
    for ext in extensions:
        files.extend(glob.glob(os.path.join(directory_path, f"*{ext}")))
    return files

def ingest_directory(directory_path, collection_name):
    print(f"Ingesting documents from {directory_path} into collection '{collection_name}'...")
    
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
        print(f"Directory didn't exist, created: {directory_path}")
        print("Please add some .txt or .md files and try again.")
        return

    # Find .txt and .md files
    txt_files = get_files(directory_path, ['.txt'])
    md_files = get_files(directory_path, ['.md'])
    
    all_files = txt_files + md_files
    if not all_files:
        print(f"No .txt or .md files found in {directory_path}. Nothing to ingest.")
        return

    print(f"Found {len(all_files)} files to ingest.")

    documents = []
    for file_path in all_files:
        print(f"Loading {file_path}...")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Add metadata if needed (filename as title, etc.)
            filename = os.path.basename(file_path)
            title = os.path.splitext(filename)[0].replace('_', ' ').replace('-', ' ').title()
            
            doc = Document(
                page_content=content,
                metadata={
                    "source": file_path,
                    "title": title,
                    "topic": "custom_upload"
                }
            )
            documents.append(doc)
            
        except Exception as e:
            print(f"Error loading {file_path}: {e}")

    if not documents:
        print("No documents were successfully loaded.")
        return

    try:
        db_manager = ChromaDBManager()
    except Exception as e:
        print(f"Error initializing DB: {e}")
        return

    # Text splitter for chunking
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )

    print("Chunking documents...")
    chunked_docs = splitter.split_documents(documents)
    print(f"  - Created {len(chunked_docs)} chunks from {len(documents)} source documents.")

    print("Adding chunks to Vector Database...")
    try:
        db_manager.add_documents(collection_name, chunked_docs)
        print("Successfully ingested documents into ChromaDB!")
    except Exception as e:
        print(f"Error adding documents to ChromaDB: {e}")


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    research_dir = os.path.join(base_dir, "raw_docs", "research")
    
    # Ingest the research documents
    ingest_directory(research_dir, "research")
