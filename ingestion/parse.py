"""Turn uploaded files into chunked LangChain documents."""
import io
import re
from pathlib import PurePath
from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from config import Config

TEXT_TYPES = {".md", ".markdown", ".txt"}
ALLOWED_TYPES = TEXT_TYPES | {".pdf"}

splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)


class ParseError(ValueError):
    """The file can't be used; the message is safe to show the user."""


def safe_name(filename: str) -> str:
    name = PurePath((filename or "").replace("\\", "/")).name
    name = re.sub(r"[^\w.\- ]", "_", name).strip(" .")[:120]
    if not name:
        raise ParseError("File has no usable name")
    return name


def file_type(filename: str) -> str:
    ext = PurePath(filename).suffix.lower()
    if ext not in ALLOWED_TYPES:
        raise ParseError(f"Unsupported file type '{ext or 'none'}'. Use .md, .txt or .pdf")
    return ext


def _pages_from_pdf(data: bytes) -> List[str]:
    if not data.startswith(b"%PDF-"):
        raise ParseError("File is not a valid PDF")
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ParseError("Password-protected PDFs are not supported")
        if len(reader.pages) > Config.UPLOAD_MAX_PAGES:
            raise ParseError(f"PDF has more than {Config.UPLOAD_MAX_PAGES} pages")
        return [page.extract_text() or "" for page in reader.pages]
    except ParseError:
        raise
    except Exception as e:
        raise ParseError(f"Could not read PDF: {type(e).__name__}") from e


def _text(data: bytes) -> str:
    if b"\x00" in data:
        raise ParseError("File is not plain text")
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise ParseError("Text files must be UTF-8") from e


def parse_file(filename: str, data: bytes, doc_id: str) -> List[Document]:
    """Parse one file into chunks tagged with file name, page and doc_id."""
    name = safe_name(filename)
    ext = file_type(name)

    if ext == ".pdf":
        pages = [(i + 1, text) for i, text in enumerate(_pages_from_pdf(data))]
    else:
        pages = [(None, _text(data))]

    docs = []
    for page, text in pages:
        if not text.strip():
            continue
        meta = {"source": name, "title": name, "doc_id": doc_id, "file_type": ext.lstrip(".")}
        if page is not None:
            meta["page"] = page
        docs.append(Document(page_content=text, metadata=meta))

    if not docs:
        hint = " It may be a scanned PDF without a text layer." if ext == ".pdf" else ""
        raise ParseError(f"No text found in {name}.{hint}")

    chunks = splitter.split_documents(docs)
    if len(chunks) > Config.UPLOAD_MAX_CHUNKS:
        raise ParseError(f"{name} is too long ({len(chunks)} chunks, max {Config.UPLOAD_MAX_CHUNKS})")
    return chunks
