"""Per-session document workspaces: upload, list and delete files to write from."""
import asyncio
import logging
import time
import uuid
from typing import Any, Dict

from fastapi import APIRouter, File, HTTPException, Path, UploadFile

from config import Config
from ingestion.parse import ParseError, parse_file, safe_name
from vector_stores.chroma import WORKSPACE_PATTERN, ChromaDBManager, workspace_collection

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/workspaces", tags=["workspaces"])

# workspace_id -> {"last_used": float, "docs": {doc_id: {...}}}
workspaces: Dict[str, Dict[str, Any]] = {}

WorkspaceId = Path(pattern=r"^[0-9a-f]{32}$")
DocId = Path(pattern=r"^[0-9a-f]{32}$")


def _db() -> ChromaDBManager:
    return ChromaDBManager()


def _drop(workspace_id: str) -> None:
    workspaces.pop(workspace_id, None)
    try:
        _db().drop_collection(workspace_collection(workspace_id))
    except Exception as e:
        logger.warning(f"Could not drop workspace {workspace_id[:8]}: {e}")


def sweep_expired(now: float = None) -> None:
    now = now or time.time()
    for wid in [w for w, ws in workspaces.items() if now - ws["last_used"] > Config.WORKSPACE_TTL_SECONDS]:
        logger.info(f"Workspace {wid[:8]} expired")
        _drop(wid)


def drop_orphaned_collections() -> None:
    """Workspaces live in memory, so collections left from an earlier process can't be reached."""
    db = _db()
    for name in db.list_collections():
        if WORKSPACE_PATTERN.match(name) and name[3:] not in workspaces:
            db.drop_collection(name)


def get_workspace(workspace_id: str) -> Dict[str, Any]:
    sweep_expired()
    ws = workspaces.get(workspace_id)
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found or expired")
    ws["last_used"] = time.time()
    return ws


def _public(doc_id: str, doc: Dict[str, Any]) -> Dict[str, Any]:
    return {"doc_id": doc_id, **doc}


@router.post("")
async def create_workspace():
    sweep_expired()
    if len(workspaces) >= Config.MAX_WORKSPACES:
        oldest = min(workspaces, key=lambda w: workspaces[w]["last_used"])
        _drop(oldest)
    workspace_id = uuid.uuid4().hex
    workspaces[workspace_id] = {"last_used": time.time(), "docs": {}}
    return {"workspace_id": workspace_id, "expires_in": Config.WORKSPACE_TTL_SECONDS}


@router.get("/{workspace_id}/documents")
async def list_documents(workspace_id: str = WorkspaceId):
    ws = get_workspace(workspace_id)
    return {"documents": [_public(d, doc) for d, doc in ws["docs"].items()]}


async def _read_limited(file: UploadFile) -> bytes:
    data = await file.read(Config.UPLOAD_MAX_BYTES + 1)
    if len(data) > Config.UPLOAD_MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"File is larger than {Config.UPLOAD_MAX_BYTES // (1024 * 1024)} MB")
    if not data:
        raise HTTPException(status_code=400, detail="File is empty")
    return data


@router.post("/{workspace_id}/documents")
async def upload_document(workspace_id: str = WorkspaceId, file: UploadFile = File(...)):
    ws = get_workspace(workspace_id)
    if len(ws["docs"]) >= Config.UPLOAD_MAX_FILES:
        raise HTTPException(status_code=400, detail=f"A workspace holds at most {Config.UPLOAD_MAX_FILES} files")
    try:
        name = safe_name(file.filename)
    except ParseError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if any(d["name"] == name for d in ws["docs"].values()):
        raise HTTPException(status_code=409, detail=f"{name} is already uploaded")

    data = await _read_limited(file)
    doc_id = uuid.uuid4().hex
    try:
        chunks = await asyncio.wait_for(asyncio.to_thread(parse_file, name, data, doc_id),
                                        timeout=Config.UPLOAD_PARSE_TIMEOUT)
    except asyncio.TimeoutError:
        raise HTTPException(status_code=422, detail=f"Reading {name} took too long")
    except ParseError as e:
        raise HTTPException(status_code=422, detail=str(e))

    try:
        await asyncio.to_thread(_db().add_documents, workspace_collection(workspace_id), chunks)
    except Exception as e:
        logger.error(f"Embedding failed for workspace {workspace_id[:8]}: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail="Could not index the file. Try again shortly.")

    # The workspace may have expired or been deleted while the file was indexing.
    if workspace_id not in workspaces:
        _drop(workspace_id)
        raise HTTPException(status_code=404, detail="Workspace not found or expired")

    pages = {c.metadata.get("page") for c in chunks if c.metadata.get("page")}
    preview = " ".join(chunks[0].page_content.split())[:Config.DOC_PREVIEW_CHARS]
    doc = {"name": name, "size": len(data), "chunks": len(chunks), "pages": len(pages) or None,
           "uploaded_at": time.time(), "preview": preview}
    ws["docs"][doc_id] = doc
    logger.info(f"Workspace {workspace_id[:8]}: indexed {name} ({len(chunks)} chunks)")
    return _public(doc_id, doc)


@router.delete("/{workspace_id}/documents/{doc_id}")
async def delete_document(workspace_id: str = WorkspaceId, doc_id: str = DocId):
    ws = get_workspace(workspace_id)
    if doc_id not in ws["docs"]:
        raise HTTPException(status_code=404, detail="Document not found")
    await asyncio.to_thread(_db().delete_documents, workspace_collection(workspace_id), doc_id)
    ws["docs"].pop(doc_id)
    return {"deleted": doc_id}


@router.delete("/{workspace_id}")
async def delete_workspace(workspace_id: str = WorkspaceId):
    get_workspace(workspace_id)
    await asyncio.to_thread(_drop, workspace_id)
    return {"deleted": workspace_id}
