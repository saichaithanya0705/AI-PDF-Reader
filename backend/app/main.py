import os
import sys
import traceback
import logging
import re

logger = logging.getLogger(__name__)

if os.getenv("DEBUG_HEARTBEAT", "").lower() in ("1", "true", "yes"):
    with open("main_heartbeat.txt", "w", encoding="utf-8") as f:
        f.write("main_loaded")

logger.info("Starting application import")
sys.stdout.flush()

try:
    import asyncio
    import uuid
    from pathlib import Path
    from typing import List, Dict, Any, Optional, Literal
    from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, WebSocket, WebSocketDisconnect, HTTPException, Query, Request, Depends
    from pydantic import BaseModel, Field
    from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.middleware.cors import CORSMiddleware
    import os
    import json
    import warnings
    import fitz  # PyMuPDF for PDF merging
    import hashlib
    from datetime import datetime
    print("✅ Basic imports successful")
    sys.stdout.flush()
except Exception as e:
    print(f"❌ FATAL: Failed to import basic modules: {e}")
    traceback.print_exc()
    sys.stdout.flush()
    raise

# Suppress NetworkX backend warnings
warnings.filterwarnings("ignore", category=UserWarning, module="vertexai")

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load from project root
    env_path = Path(__file__).parent.parent.parent / '.env'
    if env_path.exists():
        load_dotenv(env_path, override=True)
        print(f"✅ Loaded environment variables from {env_path}")
    else:
        print(f"⚠️ No .env file found at {env_path}")
except ImportError:
    print("⚠️ python-dotenv not installed, using system environment variables only")

# Setup Google Cloud credentials for Render deployment
try:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from setup_credentials import setup_google_credentials
    setup_google_credentials()
except ImportError:
    print("⚠️ setup_credentials module not found, skipping credentials setup")
except Exception as e:
    print(f"⚠️ Error setting up credentials: {e}")

print("📦 Loading websocket and models...")
sys.stdout.flush()
from .websocket_manager import manager
from .models import WebSocketMessage, SectionHighlight, RelevantSection
from .document_storage import get_document_storage
from .storage_paths import BACKEND_DIR, DATA_DIR, DOCS_DIR
print("✅ Websocket and models loaded")
sys.stdout.flush()

# The persistence module selects local SQLite/FAISS or Supabase Postgres/Storage.
print(f"🗄️ Database mode: {os.getenv('PERSISTENCE_BACKEND', 'sqlite')}")
sys.stdout.flush()

try:
    from .persistence import db
    from .document_routes import router as api_router
    from .eval_routes import router as eval_router
    from .auth_middleware import get_current_user, get_optional_user
    from .user_resolver import resolve_user_id
    print("✅ Document persistence initialized")
except Exception as e:
    print(f"❌ FATAL: Failed to initialize storage/auth dependencies: {e}")
    sys.stdout.flush()
    raise

print("📦 Loading services...")
sys.stdout.flush()
from .pdf_comparator import pdf_comparator
from .llm_providers import get_llm_provider
from .enhanced_llm_service import EnhancedLLMService
from .tts_service import TTSService
from .section_highlighter import SectionHighlighter
print("✅ Services loaded")
sys.stdout.flush()

print("📦 Loading RAG Service...")
sys.stdout.flush()
from .rag_service import CROSS_DOCUMENT_MIN_SCORE, format_retrieval_result, get_rag_service
from .ingestion_service import get_ingestion_service
print("✅ RAG Service loaded")
sys.stdout.flush()

# Create necessary directories under the canonical application data root.
print("📁 Setting up directories...")
sys.stdout.flush()
DOCS_DIR.mkdir(parents=True, exist_ok=True)
MAX_PDF_UPLOAD_BYTES = int(os.getenv("MAX_PDF_UPLOAD_BYTES", str(100 * 1024 * 1024)))
MAX_PDF_TRANSFORM_BYTES = int(os.getenv("MAX_PDF_TRANSFORM_BYTES", str(150 * 1024 * 1024)))

print(f"📁 Backend directory: {BACKEND_DIR}")
print(f"📁 Data directory: {DATA_DIR}")
print(f"📁 Docs directory: {DOCS_DIR}")
sys.stdout.flush()


def _path_is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _canonical_pdf_filename(filename: Optional[str], fallback: str = "document") -> str:
    raw_name = str(filename or fallback).replace("\\", "/").replace("\x00", "")
    basename = Path(raw_name).name
    stem = Path(basename).stem or fallback
    stem = re.sub(r"[^A-Za-z0-9._ -]+", "_", stem)
    stem = re.sub(r"\s+", "_", stem).strip(" ._-")
    if not stem:
        stem = fallback
    stem = stem[:120].rstrip(" ._-") or fallback
    return f"{stem}.pdf"


def _pdf_stem(filename: Optional[str], fallback: str = "document") -> str:
    canonical = _canonical_pdf_filename(filename, fallback=fallback)
    return canonical[:-4] if canonical.lower().endswith(".pdf") else canonical


def _safe_child_path(root: Path, filename: str) -> Path:
    raw_name = str(filename or "").replace("\\", "/").replace("\x00", "")
    if not raw_name or "/" in raw_name or raw_name in {".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid filename")

    root_path = root.resolve()
    candidate = (root_path / raw_name).resolve()
    if not _path_is_within(candidate, root_path):
        raise HTTPException(status_code=400, detail="Invalid filename")
    return candidate


def _safe_docs_path(filename: str) -> Path:
    return _safe_child_path(DOCS_DIR, filename)


def _document_pdf_path(document) -> Path:
    file_path = get_document_storage().ensure_local(document.file_path)
    if not _path_is_within(file_path, DOCS_DIR):
        raise HTTPException(status_code=404, detail="Document file not found")
    return file_path


def _delete_document_location_quietly(location: Optional[str]) -> None:
    if not location:
        return
    try:
        get_document_storage().delete(location)
    except Exception as exc:
        logger.warning("Failed to clean persisted document object %s: %s", location, exc)


def _validate_pdf_bytes(content: bytes, filename: str) -> int:
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded PDF is empty")
    if len(content) > MAX_PDF_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Uploaded PDF exceeds the size limit")
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid PDF")

    try:
        pdf_doc = fitz.open(stream=content, filetype="pdf")
        page_count = len(pdf_doc)
        pdf_doc.close()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid PDF")

    if page_count < 1:
        raise HTTPException(status_code=400, detail="Uploaded PDF has no pages")
    return page_count


def _validate_pdf_file(file_path: Path, max_bytes: int = MAX_PDF_TRANSFORM_BYTES) -> int:
    if not _path_is_within(file_path, DOCS_DIR) or not file_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found")
    if file_path.stat().st_size > max_bytes:
        raise HTTPException(status_code=413, detail="PDF exceeds the size limit")

    with open(file_path, "rb") as pdf_file:
        if pdf_file.read(5) != b"%PDF-":
            raise HTTPException(status_code=422, detail="Stored file is not a valid PDF")

    try:
        pdf_doc = fitz.open(str(file_path))
        page_count = len(pdf_doc)
        pdf_doc.close()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=422, detail="Stored file is not a valid PDF")

    if page_count < 1:
        raise HTTPException(status_code=422, detail="Stored PDF has no pages")
    return page_count


def _podcast_document_id_from_filename(filename: str) -> Optional[str]:
    match = re.fullmatch(r"podcast_([0-9a-fA-F-]{36})_[0-9]+_[0-9]+\.(wav|mp3)", filename)
    return match.group(1) if match else None

print("🚀 Creating FastAPI app...")
sys.stdout.flush()
app = FastAPI(title="Adobe Hackathon Grand Finale Backend")
print("✅ FastAPI app created")
sys.stdout.flush()

def _cors_origins() -> list:
    raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
    origins = [o.strip() for o in raw.split(",") if o.strip()]
    return origins or ["http://localhost:5173"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from starlette.middleware.base import BaseHTTPMiddleware
from .middleware.rate_limiter import default_limiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        path = request.url.path
        if path.startswith("/api/") or path.startswith("/upload"):
            client = request.client.host if request.client else "unknown"
            default_limiter.check_rate_limit(client, path)
        return await call_next(request)


app.add_middleware(RateLimitMiddleware)

# Mount static files BEFORE API routes to prevent route conflicts
# Try multiple possible paths for frontend
possible_frontend_paths = [
    Path("frontend/dist"),  # From project root
    Path("../frontend/dist"),  # From backend directory
    BACKEND_DIR.parent / "frontend" / "dist"  # Absolute path
]

frontend_dist_path = None
for path in possible_frontend_paths:
    if path.exists():
        frontend_dist_path = path
        break

if frontend_dist_path:
    # Mount assets directory for JS/CSS files with proper MIME types
    assets_path = frontend_dist_path / "assets"
    if assets_path.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_path), html=False), name="assets")
        print(f"✅ Assets mounted from {assets_path.absolute()}")
        asset_files = list(assets_path.glob("*"))
        print(f"📁 Available assets: {[f.name for f in asset_files]}")
    
    # Mount other static files (PDF.js workers, etc.)
    app.mount("/static", StaticFiles(directory=str(frontend_dist_path), html=False), name="static")
    print(f"✅ Frontend static files mounted from {frontend_dist_path.absolute()}")
else:
    print(f"⚠️ Frontend dist not found in any of: {[str(p.absolute()) for p in possible_frontend_paths]}")

# Include API routes AFTER static files
app.include_router(api_router)
app.include_router(eval_router)
# Initialize services
llm_provider = None
try:
    from .llm_providers import get_llm_provider
    llm_provider = get_llm_provider()
    logger.info("LLM provider initialized: %s", type(llm_provider).__name__)
except Exception as e:
    import traceback
    error_msg = f"LLM Provider initialization failed: {e}\n\nFull traceback:\n{traceback.format_exc()}"
    print(f"⚠️ {error_msg}")
    with open("init_error.txt", "w") as f:
        f.write(error_msg)

try:
    enhanced_llm_service = EnhancedLLMService()
    print(f"✅ Enhanced LLM Service initialized")
except Exception as e:
    print(f"⚠️ Enhanced LLM Service initialization failed: {e}")

tts_service = None
try:
    tts_service = TTSService()
    print(f"✅ TTS Service initialized")
except Exception as e:
    print(f"⚠️ TTS Service initialization failed: {e}")

highlighter = SectionHighlighter()
logger.info("Section highlighter initialized; uploads use canonical ingestion service")

# Enhanced PDF processing function with better integration
async def process_pdf(job_id: str, client_id: str, file_path: str, pdf_type: str, persona: str = None, job: str = None):
    print(f"Processing {pdf_type} job {job_id} for client {client_id}")

    try:
        await manager.send_message({
            "type": "progress",
            "job_id": job_id,
            "data": {"percent": 10, "message": "Starting ingestion..."}
        }, client_id)

        ingestion_service = get_ingestion_service()
        result = await ingestion_service.process_document(
            document_id=job_id,
            user_id=client_id,
            mode="single",
            batch_size=32,
        )

        await manager.send_message({
            "type": "progress",
            "job_id": job_id,
            "data": {
                "percent": 90 if result.get("success") else 100,
                "message": "Finalizing ingestion..." if result.get("success") else "Ingestion failed",
            }
        }, client_id)

        message_type = "complete" if result.get("success") else "error"
        await manager.send_message({
            "type": message_type,
            "job_id": job_id,
            "data": {
                "percent": 100,
                "message": "Processing Complete!" if result.get("success") else result.get("error", "Processing failed"),
                "result": {
                    **result,
                    "pdf_type": pdf_type,
                    "persona": persona,
                    "job": job,
                }
            }
        }, client_id)

        print(f"✅ Finished processing job {job_id}: {result}")

    except Exception as e:
        print(f"❌ Error processing job {job_id}: {e}")
        await manager.send_message({
            "type": "error",
            "job_id": job_id,
            "data": {"message": f"Processing failed: {str(e)}"}
        }, client_id)


async def process_pdf_collection(
    collection_job_id: str,
    client_id: str,
    document_ids: List[str],
    persona: str = None,
    job: str = None,
):
    """Process a group of uploaded PDFs through the multi-PDF algorithm."""
    job_ids = [collection_job_id, *document_ids]

    async def send_to_all(message_type: str, percent: int, message: str, result: Optional[Dict[str, Any]] = None):
        for current_job_id in job_ids:
            await manager.send_message({
                "type": message_type,
                "job_id": current_job_id,
                "data": {
                    "percent": percent,
                    "message": message,
                    **({"result": result} if result is not None else {}),
                },
            }, client_id)

    try:
        await send_to_all("progress", 10, "Starting multi-PDF ingestion...")
        ingestion_service = get_ingestion_service()
        result = await ingestion_service.process_collection(
            document_ids=document_ids,
            user_id=client_id,
            persona=persona,
            job=job,
            batch_size=32,
        )

        if result.get("success"):
            await send_to_all("complete", 100, "Processing Complete!", result)
            print(f"✅ Finished multi-PDF ingestion {collection_job_id}: {result}")
        else:
            await send_to_all("error", 100, result.get("error", "Processing failed"), result)

    except Exception as e:
        print(f"❌ Error processing multi-PDF job {collection_job_id}: {e}")
        await send_to_all("error", 100, f"Processing failed: {str(e)}")

# --- API Endpoints ---

# NEW: Endpoint for PAST/CONTEXT PDFs (bulk upload)
@app.post("/upload/context_files")
async def upload_context_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    persona: Optional[str] = Form(None),
    job: Optional[str] = Form(None),
    current_user: dict = Depends(get_current_user),
    client_id: Optional[str] = Query(None, description="Deprecated; ignored when authenticated"),
):
    """
    Accepts multiple PDF files and ingests them with the multi-PDF algorithm.
    """
    uploaded_files_info = []
    document_ids: List[str] = []
    user_id = resolve_user_id(current_user, client_id)
    collection_job_id = str(uuid.uuid4())

    logger.info("Uploading %s context files for user %s", len(files), user_id)
    sys.stdout.flush()

    for file in files:
        current_location: Optional[str] = None
        try:
            content = await file.read()
            original_name = _canonical_pdf_filename(file.filename)
            _validate_pdf_bytes(content, original_name)
            file_hash = hashlib.sha256(content).hexdigest()

            existing = db.find_duplicate_by_hash(file_hash, client_id=user_id)
            if existing:
                db.update_last_uploaded(existing.id, client_id=user_id)
                uploaded_files_info.append({
                    "job_id": existing.id,
                    "filename": original_name,
                    "status": "duplicate",
                    "is_duplicate": True,
                    "file_url": f"/api/files/{existing.filename}",
                })
                print(f"🔄 Duplicate context file detected: {original_name} (ID: {existing.id})")
                continue

            file_id = str(uuid.uuid4())
            filename_with_id = f"{file_id}_{original_name}"
            current_location = get_document_storage().store_pdf(
                user_id=user_id,
                document_id=file_id,
                filename=filename_with_id,
                content=content,
            )

            doc = db.create_document(
                document_id=file_id,
                filename=filename_with_id,
                original_name=original_name,
                file_size=len(content),
                file_path=current_location,
                client_id=user_id,
                persona=persona,
                job_role=job,
                file_hash=file_hash,
            )
            document_ids.append(doc.id)

            uploaded_files_info.append({
                "job_id": doc.id,
                "filename": original_name,
                "status": "queued",
                "file_url": f"/api/files/{filename_with_id}",
                "is_duplicate": False,
            })
            print(f"✅ Queued context file for multi-PDF ingestion: {original_name} (ID: {doc.id})")
            
        except Exception as e:
            failed_name = _canonical_pdf_filename(file.filename)
            print(f"❌ Failed to upload {failed_name}: {e}")
            uploaded_files_info.append({
                "filename": failed_name,
                "error": str(e),
                "status": "failed"
            })
            # Cleanup
            try:
                _delete_document_location_quietly(current_location)
            except Exception:
                pass

    if document_ids:
        background_tasks.add_task(
            process_pdf_collection,
            collection_job_id,
            user_id,
            document_ids,
            persona,
            job,
        )

    return JSONResponse(
        status_code=202,
        content={
            "detail": f"Accepted {len(document_ids)} new file(s) for multi-PDF ingestion",
            "collection_job_id": collection_job_id,
            "files": uploaded_files_info
        }
    )


# NEW: Endpoint for CURRENT PDF (for viewing)
@app.post("/upload/active_file")
async def upload_active_file(
    background_tasks: BackgroundTasks,
    persona: Optional[str] = Form(None),
    job: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    client_id: Optional[str] = Query(None, description="Deprecated; ignored when authenticated"),
):
    """
    Accepts a single current PDF for viewing and single-PDF ingestion.
    """
    user_id = resolve_user_id(current_user, client_id)
    file_content = await file.read()
    original_name = _canonical_pdf_filename(file.filename)
    _validate_pdf_bytes(file_content, original_name)
    file_hash = hashlib.sha256(file_content).hexdigest()

    existing = db.find_duplicate_by_hash(file_hash, client_id=user_id)
    if existing:
        db.update_last_opened(existing.id, client_id=user_id)
        return JSONResponse(
            status_code=200,
            content={
                "job_id": existing.id,
                "filename": original_name,
                "detail": "File already exists. Updated access time for existing document.",
                "file_url": f"/api/files/{existing.filename}",
                "is_duplicate": True,
                "original_upload_date": existing.upload_date.isoformat() if existing.upload_date else None,
            },
        )

    file_id = str(uuid.uuid4())
    filename_with_id = f"{file_id}_{original_name}"
    file_location = get_document_storage().store_pdf(
        user_id=user_id,
        document_id=file_id,
        filename=filename_with_id,
        content=file_content,
    )

    try:
        doc = db.create_document(
            document_id=file_id,
            filename=filename_with_id,
            original_name=original_name,
            file_size=len(file_content),
            file_path=file_location,
            client_id=user_id,
            persona=persona,
            job_role=job,
            file_hash=file_hash,
        )
    except Exception as e:
        print(f"❌ Failed to create document record: {e}")
        _delete_document_location_quietly(file_location)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    background_tasks.add_task(process_pdf, doc.id, user_id, file_location, "current", persona, job)

    return JSONResponse(
        status_code=202,
        content={
            "job_id": doc.id,
            "filename": original_name,
            "detail": "Active file accepted for viewing and processing.",
            "file_url": f"/api/files/{filename_with_id}",
            "is_duplicate": False,
        },
    )


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """Handles the WebSocket connection for real-time updates. (Unchanged)"""
    await manager.connect(websocket, client_id)
    try:
        while True:
            await websocket.receive_text() # Keep connection alive
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        print(f"Client #{client_id} disconnected")

# --- Frontend Serving ---
@app.get("/")
async def get_frontend():
    """Serve the built React frontend"""
    # Try multiple possible paths
    possible_paths = [
        Path("frontend/dist/index.html"),  # From project root
        Path("../frontend/dist/index.html"),  # From backend directory
        BACKEND_DIR.parent / "frontend" / "dist" / "index.html"  # Absolute path
    ]
    
    for html_file in possible_paths:
        if html_file.exists():
            return HTMLResponse(content=html_file.read_text(), media_type="text/html")
    
    return HTMLResponse(content=f"<h1>Frontend not found. Tried: {[str(p.absolute()) for p in possible_paths]}. Please build the React app first.</h1>", media_type="text/html")


@app.get("/healthz", include_in_schema=False)
async def healthcheck():
    """Lightweight liveness check used by Render and container runtimes."""
    return {"status": "ok"}


@app.get("/config")
async def get_config():
    """
    Provides necessary client-side configuration, like API keys.
    """
    client_id = os.getenv("ADOBE_CLIENT_ID", "a46749c05a8048448b7a9735e020a6f7")  # Fallback for demo
    return {
        "adobeClientId": client_id,
        "llmProvider": os.getenv("LLM_PROVIDER", "gemini"),
        "ttsProvider": os.getenv("TTS_PROVIDER", "azure"),
        "features": {
            "llmEnabled": llm_provider is not None,
            "ttsEnabled": tts_service is not None
        }
    }


def _document_display_name(document: Any) -> str:
    return document.original_name or document.filename or f"Document {document.id[:8]}"


def _recommendation_from_retrieval_result(result: Any, doc_name_cache: Dict[str, str]) -> Dict[str, Any]:
    formatted = format_retrieval_result(result, snippet_chars=200)
    document_id = formatted.get("document_id")
    relevance = formatted.get("retrieval_score")
    if relevance is None:
        relevance = formatted.get("vector_similarity", formatted.get("similarity", 0.0))

    return {
        "id": formatted.get("id"),
        "title": formatted.get("section_title") or "Relevant section",
        "snippet": formatted.get("text", ""),
        "page": formatted.get("page_number") or 1,
        "relevance": relevance or 0.0,
        "similarity": formatted.get("similarity", 0.0),
        "vector_similarity": formatted.get("vector_similarity", 0.0),
        "retrieval_score": formatted.get("retrieval_score"),
        "lexical_overlap": formatted.get("lexical_overlap"),
        "rerank_score": formatted.get("rerank_score"),
        "documentId": document_id,
        "documentName": doc_name_cache.get(document_id, formatted.get("document_name", "Unknown Document")),
        "bbox": None,
        "file_path": formatted.get("file_path", ""),
    }


@app.get("/api/recommendations/{document_id}")
async def get_recommendations(
    document_id: str,
    page: int = Query(1, ge=1),
    persona: str = Query(None),
    job: str = Query(None),
    include_cross_document: bool = Query(True, description="Include cross-document recommendations"),
    current_user: dict = Depends(get_current_user)
):
    """Get related sections for a specific document and page with intelligent cross-document connections"""
    try:
        user_id = current_user["sub"]

        current_document = db.get_document_by_id(document_id, client_id=user_id)
        if not current_document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Build a cache of document names from database
        doc_name_cache = {current_document.id: _document_display_name(current_document)}
        try:
            all_docs = db.get_all_documents(client_id=user_id)
            for doc in all_docs:
                doc_name_cache[doc.id] = _document_display_name(doc)
        except Exception as e:
            print(f"⚠️ Could not fetch document names: {e}")

        from .context_builder import get_page_content

        page_content = await get_page_content(db, user_id, document_id, page)
        if page_content:
            current_content = page_content[:2000]
        else:
            metadata = current_document.metadata or {}
            topics = metadata.get("topics") or []
            current_content = "\n".join(
                str(part)
                for part in [
                    _document_display_name(current_document),
                    metadata.get("summary"),
                    ", ".join(str(topic) for topic in topics[:8]) if isinstance(topics, list) else topics,
                    f"Page {page}",
                ]
                if part
            )

        # Enhanced query with persona and job context
        if persona and job:
            current_content += f" Context: {persona} working on {job}"

        rag_service = get_rag_service()
        same_document_results = await rag_service.search_documents(
            query=current_content,
            top_k=3,
            document_id=document_id,
            user_id=user_id,
            use_advanced_rag=False,
        )

        cross_document_results = []
        if include_cross_document:
            cross_document_results = await rag_service.search_documents(
                query=current_content,
                top_k=5 if persona and job else 3,
                exclude_document_id=document_id,
                user_id=user_id,
                use_advanced_rag=False,
            )

        same_document_recommendations = [
            _recommendation_from_retrieval_result(result, doc_name_cache)
            for result in same_document_results
        ]
        cross_document_recommendations = [
            _recommendation_from_retrieval_result(result, doc_name_cache)
            for result in cross_document_results
        ]

        # Enhanced cross-document intelligence using the intelligent PDF brain
        enhanced_cross_document = cross_document_recommendations[:3]
        if include_cross_document and cross_document_recommendations and persona and job:
            enhanced_cross_document = []
            try:
                # Initialize the intelligent PDF brain
                from .utils.intelligent_pdf_brain import DocumentSection, IntelligentPDFBrain
                brain = IntelligentPDFBrain()

                # Score cross-document sections using intelligent analysis
                for rec in cross_document_recommendations[:5]:  # Limit to top 5 for processing
                    # The scorer reads key_entities/key_concepts, so use the real
                    # dataclass rather than an ad-hoc object missing those fields.
                    section = DocumentSection(
                        document=rec['documentName'],
                        section_title=rec['title'],
                        content=rec['snippet'],
                        page_number=rec['page'],
                    )
                    
                    # Calculate enhanced relevance using the brain's intelligence
                    try:
                        enhanced_score = brain.calculate_enhanced_relevance_score(section, persona, job)
                        rec['enhanced_relevance'] = enhanced_score
                        rec['intelligence_explanation'] = f"Intelligent analysis for {persona}: {enhanced_score:.2f} relevance"
                        
                        # Only include if enhanced score is significant
                        if enhanced_score > 0.5:
                            enhanced_cross_document.append(rec)
                    except Exception as e:
                        print(f"Error calculating enhanced relevance: {e}")
                        # Fallback to original relevance
                        enhanced_cross_document.append(rec)
                
                # Sort by enhanced relevance if available, otherwise by original relevance
                enhanced_cross_document.sort(
                    key=lambda x: x.get('enhanced_relevance', x['relevance']), 
                    reverse=True
                )
                
            except Exception as e:
                print(f"Error in intelligent cross-document analysis: {e}")
                enhanced_cross_document = cross_document_recommendations[:3]
        
        # Drop weak filler so the side panel only shows genuinely related pages.
        enhanced_cross_document = [
            rec for rec in enhanced_cross_document
            if (rec.get("relevance") or 0.0) >= CROSS_DOCUMENT_MIN_SCORE
        ]

        # Return top 3 same-document and top 3 cross-document recommendations
        result = {
            "recommendations": same_document_recommendations[:3],
            "cross_document_sections": enhanced_cross_document[:3] if include_cross_document else [],
            "total_found": len(same_document_recommendations) + len(cross_document_recommendations),
            "intelligence_enabled": include_cross_document and persona and job
        }
        
        print(f"📊 Recommendations for {document_id} page {page}: {len(result['recommendations'])} same-doc, {len(result['cross_document_sections'])} cross-doc")
        
        return result

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting recommendations: {e}")
        return {"recommendations": [], "cross_document_sections": []}


@app.get("/api/insights/{document_id}")
async def get_insights(
    document_id: str,
    page: int = Query(1, ge=1),
    persona: str = Query(None),
    job: str = Query(None),
    current_user: dict = Depends(get_current_user)
):
    """Generate comprehensive AI-powered insights for a specific document and page using actual PDF content"""
    try:
        if not enhanced_llm_service:
            raise HTTPException(status_code=503, detail="Enhanced LLM service not available")

        user_id = current_user["sub"]

        # Get the actual document from database
        document = db.get_document_by_id(document_id, client_id=user_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Extract FULL PDF content for comprehensive AI analysis
        page_content = ""
        full_pdf_content = ""
        full_content = ""

        try:
            import fitz  # PyMuPDF

            # Handle both absolute and relative paths
            pdf_path = Path(document.file_path)
            if not pdf_path.is_absolute():
                # If relative, make it relative to the backend directory
                backend_dir = Path(__file__).parent.parent
                pdf_path = backend_dir / pdf_path

            print(f"🔍 Looking for PDF at: {pdf_path}")
            print(f"🔍 Absolute path: {pdf_path.absolute()}")
            print(f"🔍 File exists: {pdf_path.exists()}")

            if not pdf_path.exists():
                raise HTTPException(status_code=404, detail="PDF file not found")

            pdf_doc = fitz.open(pdf_path)
            total_pages = len(pdf_doc)
            if page > total_pages:
                pdf_doc.close()
                raise HTTPException(status_code=422, detail="Requested page is outside the PDF page range")

            all_pages_content = []
            for page_num in range(total_pages):
                page_text = pdf_doc[page_num].get_text()
                if page_text.strip():
                    all_pages_content.append(f"=== Page {page_num + 1} ===\n{page_text}")

            current_page = pdf_doc[page - 1]
            page_content = current_page.get_text()
            full_pdf_content = "\n\n".join(all_pages_content)

            full_content = f"""DOCUMENT: {document.original_name}
TOTAL PAGES: {total_pages}
CURRENT PAGE FOCUS: {page}

CURRENT PAGE CONTENT:
{page_content}

COMPLETE DOCUMENT CONTENT:
{full_pdf_content[:15000]}{'...' if len(full_pdf_content) > 15000 else ''}"""

            pdf_doc.close()
            print(f"📄 Extracted full PDF: {total_pages} pages, {len(full_pdf_content)} characters total")

        except HTTPException:
            raise
        except Exception as e:
            print(f"Error extracting PDF content: {e}")
            raise HTTPException(status_code=422, detail="Could not extract document content for insights")

        if not full_content.strip():
            raise HTTPException(status_code=422, detail="No document text is available for insights")

        print(f"🧠 Generating comprehensive insights for {document.original_name}")
        print(f"📊 PDF file: {document.file_path}")
        print(f"📄 Page focus: {page}, Full document analysis: enabled")

        related_sections = []
        try:
            all_documents = db.get_all_documents(client_id=user_id)
            for doc in all_documents[:3]:
                if doc.id != document_id and hasattr(db, "get_document_metadata"):
                    doc_metadata = db.get_document_metadata(doc.id, client_id=user_id)
                    if doc_metadata:
                        for meta in doc_metadata[:2]:
                            related_sections.append({
                                'title': f"{doc.original_name} - Page {meta.get('page', 1)}",
                                'snippet': meta.get('text', '')[:200] + '...' if len(meta.get('text', '')) > 200 else meta.get('text', ''),
                                'document_id': doc.id,
                                'page': meta.get('page', 1)
                            })
        except Exception as e:
            print(f"Warning: Could not get related sections: {e}")

        try:
            print("🧠 Using Enhanced LLM Service for insights generation...")
            insights = await enhanced_llm_service.generate_insights_bulb(
                content=full_content,
                related_sections=related_sections,
                persona=persona or "General Reader",
                job=job or "Document Analysis"
            )

            # Add IDs to insights if they don't have them
            for i, insight in enumerate(insights):
                if 'id' not in insight:
                    insight['id'] = str(i + 1)

            print(f"✅ Successfully generated {len(insights)} insights")
            for i, insight in enumerate(insights):
                print(f"  {i+1}. {insight.get('type', 'unknown')}: {insight.get('title', 'No title')}")

            return {"insights": insights}
            
        except Exception:
            logger.exception("LLM failed to generate insights")
            raise HTTPException(status_code=502, detail="Insight generation failed")

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error generating insights: {e}")
        logger.exception("Error generating insights")
        raise HTTPException(status_code=500, detail="Failed to generate insights")


@app.post("/api/generate-podcast")
async def generate_podcast(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Generate a podcast-style audio overview with Azure TTS"""
    try:
        if not tts_service:
            raise HTTPException(status_code=503, detail="TTS service not available")

        # Parse request body
        body = await request.json()
        document_id = body.get("document_id")
        try:
            page = int(body.get("page", 1))
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Page must be a positive integer")
        if page < 1:
            raise HTTPException(status_code=400, detail="Page must be a positive integer")
        selected_text = body.get("selected_text")
        persona = body.get("persona")
        job = body.get("job")
        user_id = current_user["sub"]

        if not document_id:
            raise HTTPException(status_code=400, detail="Document ID is required")

        document = db.get_document_by_id(document_id, client_id=user_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document was not found")

        print(f"🎙️ Generating podcast for document {document_id}, page {page}")
        print(f"📝 Selected text: {selected_text[:100] if selected_text else 'None'}...")

        # Determine content source
        if selected_text and len(selected_text.strip()) > 10:
            # Use selected text
            content = selected_text.strip()
            title = f"Selected Text from {document.original_name}"
            print(f"🎯 Using selected text ({len(content)} chars)")
        else:
            # Try to get actual document content
            try:
                # Try to extract content from the PDF after tenant and storage checks.
                pdf_path = _document_pdf_path(document)
                _validate_pdf_file(pdf_path)
                import PyPDF2
                with open(pdf_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    if page <= len(pdf_reader.pages):
                        page_content = pdf_reader.pages[page - 1].extract_text()
                        content = page_content[:2000]  # Limit for reasonable audio length
                        title = f"{document.original_name} - Page {page}"
                        print(f"📄 Using PDF content ({len(content)} chars)")
                    else:
                        raise HTTPException(status_code=422, detail="Requested page is outside the PDF page range")
            except HTTPException:
                raise
            except Exception as e:
                print(f"⚠️ Could not extract PDF content: {e}")
                raise HTTPException(status_code=422, detail="Could not extract document content for podcast")

        if not content or not content.strip():
            raise HTTPException(status_code=422, detail="No document text is available for podcast generation")

        # Add persona context
        if persona and job:
            content = f"As a {persona} working on {job}, here's what you need to know: {content}"

        # Generate audio using Azure TTS (now with proper audio_config)
        print(f"🔊 Generating audio with Azure TTS...")
        try:
            audio_data = await tts_service.generate_podcast(content, title)

            # Save with a document-bound filename so playback can be authorized later.
            filename = f"podcast_{document_id}_{page}_{hash(content) % 10000}.wav"
            audio_dir = DATA_DIR / "temp_audio"
            audio_dir.mkdir(parents=True, exist_ok=True)
            audio_file = _safe_child_path(audio_dir, filename)
            with open(audio_file, "wb") as f:
                f.write(audio_data)

            print(f"✅ Podcast generated: {audio_file}")
            return {"audioUrl": f"/api/audio/{audio_file.name}"}

        except Exception as tts_error:
            print(f"⚠️ Azure TTS failed: {tts_error}")
            raise HTTPException(status_code=502, detail="TTS generation failed")

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error generating podcast: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Old endpoints removed - now using proper API routes in api_routes.py

@app.get("/api/files/{filename}")
@app.head("/api/files/{filename}")
async def get_pdf_file(filename: str, current_user: dict = Depends(get_current_user)):
    """Serve an owned uploaded PDF for PDF.js and Adobe PDF Embed API."""
    user_id = current_user["sub"]
    document = db.get_document_by_filename(filename, client_id=user_id)
    if not document:
        raise HTTPException(status_code=404, detail="PDF file not found")

    file_path = _document_pdf_path(document)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="PDF file not found")
    _validate_pdf_file(file_path)

    return FileResponse(
        file_path,
        media_type="application/pdf",
        headers={
            "Accept-Ranges": "bytes",
            "Cache-Control": "private, max-age=3600",
            "Content-Disposition": f"inline; filename={document.original_name}",
        }
    )


@app.get("/api/audio/{filename}")
async def get_audio(filename: str, current_user: dict = Depends(get_current_user)):
    """Serve generated audio files after verifying document ownership."""
    user_id = current_user["sub"]
    document_id = _podcast_document_id_from_filename(filename)
    if not document_id:
        raise HTTPException(status_code=404, detail="Audio file not found")

    document = db.get_document_by_id(document_id, client_id=user_id)
    if not document:
        raise HTTPException(status_code=404, detail="Audio file not found")

    audio_path = _safe_child_path(DATA_DIR / "temp_audio", filename)
    if audio_path.exists():
        media_type = "audio/wav" if filename.endswith('.wav') else "audio/mpeg"
        return FileResponse(
            audio_path,
            media_type=media_type,
            headers={
                "Accept-Ranges": "bytes",
                "Cache-Control": "public, max-age=3600",
                "Content-Disposition": f"inline; filename={filename}"
            }
        )

    raise HTTPException(status_code=404, detail="Audio file not found")


class AskGPTRequest(BaseModel):
    selected_text: str
    context: str = ""
    persona: str = None
    job: str = None

@app.post("/api/ask-gpt")
async def ask_gpt(request: AskGPTRequest, current_user: dict = Depends(get_current_user)):
    """Get GPT response for selected text - Enhanced with new LLM service"""
    try:
        if not enhanced_llm_service:
            # Fallback to original implementation
            if not llm_provider:
                raise HTTPException(status_code=503, detail="LLM provider not available")

            prompt = f"""
            User Profile: {request.persona or 'General Reader'}
            Task: {request.job or 'Understanding the content'}

            Selected Text: "{request.selected_text}"
            Context: {request.context}

            Please provide a helpful explanation of this text in the context of the user's needs.
            """

            response = await llm_provider.generate_text(prompt, 300)
            return {"response": response.content}

        # Use enhanced LLM service
        insights = await enhanced_llm_service.generate_text_selection_insights(
            request.selected_text, request.context, request.persona, request.job
        )

        return {
            "response": insights.get("explanation", "Analysis completed"),
            "insights": insights
        }

    except Exception as e:
        print(f"Error in ask-gpt: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class TextSelectionAnalysisRequest(BaseModel):
    selected_text: str
    document_id: str
    page: int = 1
    persona: str = None
    job: str = None
    include_cross_document: bool = True

@app.post("/api/text-selection-analysis")
async def analyze_text_selection(request: TextSelectionAnalysisRequest, current_user: dict = Depends(get_current_user)):
    """
    Core Hackathon Feature: Analyze selected text and find related sections across documents
    This is the main endpoint for the text selection → cross-document search flow
    """
    try:
        if not enhanced_llm_service:
            raise HTTPException(status_code=503, detail="Enhanced LLM service not available")

        user_id = current_user["sub"]
        
        current_doc = db.get_document_by_id(request.document_id, client_id=user_id)
            
        if not current_doc:
            raise HTTPException(status_code=404, detail="Document not found")

        context = f"Document: {current_doc.original_name} (Page {request.page})"

        # Generate insights for selected text
        text_insights = await enhanced_llm_service.generate_text_selection_insights(
            request.selected_text, context, request.persona, request.job
        )

        related_sections = []
        cross_document_sections = []

        if request.include_cross_document:
            try:
                # Use RAG Service for search
                rag_service = get_rag_service()
                
                # Search for similar chunks
                search_results = await rag_service.search_documents(
                    query=request.selected_text,
                    top_k=20,  # Get more candidates for LLM filtering
                    user_id=user_id
                )
                
                # Prepare sections for LLM analysis
                candidate_sections = []
                for i, res in enumerate(search_results):
                    formatted = format_retrieval_result(res, snippet_chars=200)
                    # Fetch document name if missing (SearchResult might not have it if not in metadata)
                    doc_name = formatted.get("document_name", "Unknown Document")
                    if res.document_id == request.document_id:
                        doc_name = _document_display_name(current_doc)
                    
                    candidate_sections.append({
                        "section_id": i,
                        "document_id": res.document_id,
                        "document_name": doc_name,
                        "title": formatted.get("section_title", "Untitled"),
                        "content": res.chunk_text,
                        "page": res.page_number,
                        "faiss_score": formatted.get("vector_similarity", 0.0),
                        "vector_similarity": formatted.get("vector_similarity", 0.0),
                        "retrieval_score": formatted.get("retrieval_score"),
                    })

                # Use LLM to find truly related sections
                related_sections = await enhanced_llm_service.find_related_sections(
                    request.selected_text, candidate_sections, request.persona, request.job, max_results=5
                )

                # Separate current document vs cross-document sections
                for section in related_sections:
                    if section.get("document_id") == request.document_id:
                        # Same document - add to related sections
                        pass  # Could add same-document sections here
                    else:
                        # Different document - add to cross-document sections
                        cross_document_sections.append(section)

            except Exception as e:
                print(f"Error in cross-document search: {e}")

        # Generate insights bulb content
        insights_bulb = await enhanced_llm_service.generate_insights_bulb(
            request.selected_text, related_sections[:3], request.persona, request.job
        )

        return {
            "selected_text": request.selected_text,
            "text_insights": text_insights,
            "related_sections": related_sections,
            "cross_document_sections": cross_document_sections,
            "insights_bulb": insights_bulb,
            "metadata": {
                "document_id": request.document_id,
                "page": request.page,
                "persona": request.persona,
                "job": request.job,
                "total_related": len(related_sections),
                "total_cross_document": len(cross_document_sections)
            }
        }

    except Exception as e:
        print(f"Error in text selection analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/ask-gemini-selection")
async def ask_gemini_selection(request: dict, current_user: dict = Depends(get_current_user)):
    """Ask Gemini to explain selected text with context"""
    try:
        document_id = request.get('document_id')
        selected_text = request.get('selected_text', '')
        page = request.get('page', 1)
        context_chars = request.get('context_chars', 500)
        
        user_id = current_user["sub"]

        if not document_id or not selected_text:
            return {"error": "Missing document_id or selected_text"}

        document = db.get_document_by_id(document_id, client_id=user_id)
            
        if not document:
            return {"error": "Document not found"}

        # Extract context around the selected text
        context_text = ""
        try:
            import fitz  # PyMuPDF

            # Handle both absolute and relative paths
            pdf_path = Path(document.file_path)
            if not pdf_path.is_absolute():
                backend_dir = Path(__file__).parent.parent
                pdf_path = backend_dir / pdf_path

            if pdf_path.exists():
                pdf_doc = fitz.open(pdf_path)
                if page <= len(pdf_doc):
                    current_page = pdf_doc[page - 1]
                    full_page_text = current_page.get_text()

                    # Find the selected text in the page
                    selected_index = full_page_text.find(selected_text)
                    if selected_index != -1:
                        # Get context before and after
                        start_index = max(0, selected_index - context_chars)
                        end_index = min(len(full_page_text), selected_index + len(selected_text) + context_chars)
                        context_text = full_page_text[start_index:end_index]
                    else:
                        # If exact match not found, use the selected text with some page context
                        context_text = f"Selected text: {selected_text}\n\nPage context:\n{full_page_text[:1000]}"

                pdf_doc.close()
            else:
                context_text = selected_text

        except Exception as e:
            print(f"Error extracting context: {e}")
            context_text = selected_text

        # Ask Gemini to explain the text
        from .chat_with_llm import get_llm_response

        prompt = f"""Please explain the following text in a clear and concise way. Provide context about what this text means, its significance, and any important details someone should know about it.

Selected Text: "{selected_text}"

Context: {context_text}

Please provide a helpful explanation that:
1. Explains what this text means
2. Provides relevant context or background
3. Highlights any important concepts or terms
4. Is easy to understand

Keep the explanation concise but informative (2-3 paragraphs maximum)."""

        explanation = await asyncio.to_thread(get_llm_response, [{"role": "user", "content": prompt}])

        return {
            "explanation": explanation,
            "selected_text": selected_text,
            "document_name": document.original_name
        }

    except Exception as e:
        print(f"Error in ask_gemini_selection: {e}")
        return {"error": f"Failed to get explanation: {str(e)}"}


@app.get("/api/highlights/{document_id}")
async def get_section_highlights(
    document_id: str,
    page: int = Query(1, ge=1),
    current_user: dict = Depends(get_current_user)
):
    """Get section highlighting data for PDF overlay"""
    try:
        # First get recommendations for this page
        recommendations_response = await get_recommendations(
            document_id=document_id,
            page=page,
            current_user=current_user
        )
        recommendations = recommendations_response.get("recommendations", [])

        if not recommendations:
            return {"highlights": [], "annotations": []}

        # Get highlight coordinates
        highlights = highlighter.get_section_highlights(document_id, page, recommendations)

        # Create overlay data for frontend
        overlay_data = highlighter.create_highlight_overlay_data(highlights)

        return overlay_data

    except Exception as e:
        print(f"Error getting highlights: {e}")
        return {"highlights": [], "annotations": [], "error": str(e)}


@app.post("/api/split-document")
async def split_document(request: Request, current_user: dict = Depends(get_current_user)):
    """Split a PDF document into multiple PDFs based on page ranges"""
    try:
        body = await request.json()
        document_id = body.get("document_id")
        splits = body.get("splits", [])  # List of {name, start_page, end_page}
        user_id = current_user["sub"]

        if not document_id:
            raise HTTPException(status_code=400, detail="Document ID is required")

        if len(splits) < 2:
            raise HTTPException(status_code=400, detail="At least 2 splits required")

        print(f"✂️ Splitting document {document_id} into {len(splits)} parts")

        # Get document from database with tenant scope.
        document = db.get_document_by_id(document_id, client_id=user_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        pdf_path = _document_pdf_path(document)

        # Validate page ranges
        total_pages = _validate_pdf_file(pdf_path)

        # Check page ranges for validity and overlaps
        used_pages = set()
        for i, split in enumerate(splits):
            start_page = split.get("start_page", 1)
            end_page = split.get("end_page", 1)

            # Validate page numbers
            if start_page < 1 or end_page > total_pages or start_page > end_page:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid page range for split {i+1}: {start_page}-{end_page}. Document has {total_pages} pages."
                )

            # Check for overlaps
            split_pages = set(range(start_page, end_page + 1))
            overlap = used_pages.intersection(split_pages)
            if overlap:
                raise HTTPException(
                    status_code=400,
                    detail=f"Page overlap detected in split {i+1}: pages {sorted(overlap)} are already used"
                )
            used_pages.update(split_pages)

        # Perform the split
        created_documents = []
        source_doc = fitz.open(str(pdf_path))

        for i, split in enumerate(splits):
            start_page = split.get("start_page", 1) - 1  # Convert to 0-based indexing
            end_page = split.get("end_page", 1) - 1
            split_name = str(split.get("name") or "").strip()

            # Generate name if not provided
            if not split_name:
                split_name = f"{_pdf_stem(document.original_name)}_part_{i+1}"
            output_display_name = _canonical_pdf_filename(split_name, fallback=f"split_part_{i+1}")
            split_name = _pdf_stem(output_display_name)

            print(f"  Creating split {i+1}: {split_name} (pages {start_page+1}-{end_page+1})")

            # Create new document for this split
            split_doc = fitz.open()
            split_doc.insert_pdf(source_doc, from_page=start_page, to_page=end_page)

            # Save split document
            output_document_id = str(uuid.uuid4())
            output_filename = f"{output_document_id}_{output_display_name}"
            output_path = _safe_docs_path(output_filename)
            split_doc.save(str(output_path))
            split_doc.close()
            _validate_pdf_file(output_path)

            # Calculate file hash and size
            output_location = None
            try:
                file_size = output_path.stat().st_size
                output_content = output_path.read_bytes()
                file_hash = hashlib.sha256(output_content).hexdigest()
                output_location = get_document_storage().store_pdf(
                    user_id=user_id,
                    document_id=output_document_id,
                    filename=output_filename,
                    content=output_content,
                )
                new_document = db.create_document(
                    document_id=output_document_id,
                    filename=output_filename,
                    original_name=output_display_name,
                    file_size=file_size,
                    file_path=output_location,
                    client_id=user_id,
                    persona=document.persona or "System",
                    job_role=document.job_role or "PDF Split",
                    file_hash=file_hash
                )

                created_documents.append({
                    "id": new_document.id,
                    "name": output_display_name,
                    "filename": output_filename,
                    "size": file_size,
                    "pages": end_page - start_page + 1,
                    "page_range": f"{start_page+1}-{end_page+1}"
                })

            except Exception as persistence_error:
                _delete_document_location_quietly(output_location)
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to persist split document: {str(persistence_error)}",
                )
            finally:
                output_path.unlink(missing_ok=True)

        source_doc.close()

        print(f"✅ Successfully split {document.original_name} into {len(created_documents)} documents")

        return {
            "success": True,
            "original_document": {
                "id": document.id,
                "name": document.original_name
            },
            "split_documents": created_documents,
            "message": f"Successfully split '{document.original_name}' into {len(created_documents)} documents"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error splitting document: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to split document: {str(e)}")


@app.post("/api/merge-documents")
async def merge_documents(request: Request, current_user: dict = Depends(get_current_user)):
    """Merge multiple PDF documents into a single PDF"""
    try:
        body = await request.json()
        document_ids = body.get("document_ids", [])
        output_name = str(body.get("output_name") or "").strip()
        user_id = current_user["sub"]

        if len(document_ids) < 2:
            raise HTTPException(status_code=400, detail="At least 2 documents required for merging")

        print(f"🔗 Merging {len(document_ids)} documents")
        print(f"📝 Output name: '{output_name}' (empty will auto-generate)")

        # Get documents from database
        documents = []
        for doc_id in document_ids:
            doc = db.get_document_by_id(doc_id, client_id=user_id)
            if not doc:
                raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
            documents.append(doc)

        # Verify all files exist
        pdf_paths = []
        for doc in documents:
            pdf_path = _document_pdf_path(doc)
            _validate_pdf_file(pdf_path)
            pdf_paths.append(pdf_path)

        # Generate output filename
        if not output_name:
            # Auto-generate name: merged_pdf_1, merged_pdf_2, etc.
            counter = 1
            while True:
                auto_name = f"merged_pdf_{counter}"
                # Check if this name already exists in database
                existing = db.search_documents(auto_name, client_id=user_id)
                if not any(doc.original_name.startswith(auto_name) for doc in existing):
                    output_name = auto_name
                    break
                counter += 1
        output_display_name = _canonical_pdf_filename(output_name, fallback="merged_pdf")
        output_name = _pdf_stem(output_display_name)

        # Create merged PDF using PyMuPDF
        merged_doc = fitz.open()
        total_pages = 0

        print(f"🔄 Starting PDF merge process...")
        for i, (doc, pdf_path) in enumerate(zip(documents, pdf_paths), 1):
            print(f"  Processing {i}/{len(documents)}: {doc.original_name}")
            source_doc = fitz.open(str(pdf_path))
            page_count = len(source_doc)
            merged_doc.insert_pdf(source_doc)
            source_doc.close()
            total_pages += page_count
            print(f"    Added {page_count} pages (total: {total_pages})")

        # Save merged PDF
        output_document_id = str(uuid.uuid4())
        output_filename = f"{output_document_id}_{output_display_name}"
        output_path = _safe_docs_path(output_filename)
        merged_doc.save(str(output_path))
        merged_doc.close()
        _validate_pdf_file(output_path)

        output_location = None
        try:
            file_size = output_path.stat().st_size
            output_content = output_path.read_bytes()
            file_hash = hashlib.sha256(output_content).hexdigest()
            output_location = get_document_storage().store_pdf(
                user_id=user_id,
                document_id=output_document_id,
                filename=output_filename,
                content=output_content,
            )
            new_document = db.create_document(
                document_id=output_document_id,
                filename=output_filename,
                original_name=output_display_name,
                file_size=file_size,
                file_path=output_location,
                client_id=user_id,
                persona="System",
                job_role="PDF Merge",
                file_hash=file_hash
            )
            new_doc_id = new_document.id
        except Exception as persistence_error:
            _delete_document_location_quietly(output_location)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to persist merged document: {str(persistence_error)}",
            )
        finally:
            output_path.unlink(missing_ok=True)

        print(f"✅ Successfully merged {len(documents)} documents into: {output_name}.pdf")
        print(f"📊 Total pages: {total_pages}, File size: {file_size} bytes")

        return {
            "success": True,
            "merged_document": {
                "id": new_doc_id,
                "name": f"{output_name}.pdf",
                "filename": output_filename,
                "size": file_size,
                "pages": total_pages,
                "source_documents": len(documents)
            },
            "message": f"Successfully merged {len(documents)} documents into '{output_name}.pdf'"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error merging documents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to merge documents: {str(e)}")


# Library Statistics Endpoint for Chatbot Context
@app.get("/api/library/statistics")
async def get_library_statistics(current_user: dict = Depends(get_current_user)):
    """
    Get library statistics for chatbot context
    Returns document counts, types, and recent activity
    """
    try:
        user_id = current_user["sub"]
        
        # Import context builder
        from .context_builder import build_library_context
        
        # Build library context
        context = await build_library_context(db=db, user_id=user_id)
        
        return {
            "success": True,
            **context,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting library statistics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get library statistics: {str(e)}")


# Chat endpoint for AI assistant
class ChatRequest(BaseModel):
    message: str
    document_id: Optional[str] = None
    current_page: Optional[int] = None
    context_type: Literal["library", "pdf_viewer"] = "library"
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)
    session_id: Optional[str] = None

@app.post("/api/chat")
async def chat_endpoint(
    request: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Handle chat messages with AI assistant using context-aware RAG
    Supports library and PDF viewer contexts with semantic search
    """
    try:
        if not llm_provider:
            raise HTTPException(status_code=503, detail="LLM service not available")

        user_id = current_user["sub"]
        
        if os.getenv("DEBUG_CHAT_LOGGING", "false").lower() == "true":
            with open("backend_debug.log", "a", encoding="utf-8") as f:
                f.write(f"\n--- Request at {datetime.now().isoformat()} ---\n")
                f.write(f"User ID: {user_id}\n")
                f.write(f"Message Length: {len(request.message)}\n")
                f.write(f"Context Type: {request.context_type}\n")

        print(f"👤 User ID: {user_id}")
        
        # Import context builder and RAG service  
        from .context_builder import build_library_context, build_pdf_context, build_enriched_messages, search_library_documents
        from .rag_service import get_rag_service
        from .chat_history import get_chat_history_manager
        
        # Initialize chat history manager
        chat_mgr = get_chat_history_manager()
        
        # Revalidate the requested session against the authenticated user.
        session_id = request.session_id
        if session_id:
            existing_session = await chat_mgr.get_session(session_id, user_id)
            if not existing_session:
                print(f"⚠️ Session {session_id} missing or unauthorized for user {user_id}; creating a new session")
                session_id = None

        if not session_id:
            print("🆕 Creating new chat session...")
            session_id = await chat_mgr.create_session(
                user_id=user_id,
                title=request.message[:50] + "..." if len(request.message) > 50 else request.message,
                context_type=request.context_type
            )
            print(f"✅ Session created: {session_id}")
        
        # Save user message
        print("💾 Saving user message...")
        await chat_mgr.save_message(
            user_id=user_id,
            session_id=session_id,
            role="user",
            content=request.message
        )
        print("✅ User message saved")
        
        # Build context based on context_type
        print(f"📍 Context type: {request.context_type}")
        
        if request.context_type == "pdf_viewer" and request.document_id:
            # PDF viewer context
            print(f"📄 Building PDF context for document: {request.document_id}, page: {request.current_page}")
            context = await build_pdf_context(
                db=db,
                user_id=user_id,
                document_id=request.document_id,
                current_page=request.current_page
            )
            
            # Use RAG for PDF-specific questions
            rag_service = get_rag_service()
            rag_result = await rag_service.generate_rag_response(
                query=request.message,
                llm_provider=llm_provider,
                document_id=request.document_id,
                user_id=user_id,
                top_k=5,
                max_tokens=500,
                conversation_history=request.conversation_history
            )
            
            response_text = rag_result['response']
            sources = rag_result.get('sources', [])

            # Fetch cross-document suggestions for the "Related in Library" feature
            cross_doc_suggestions = []
            try:
                # Search for related content in OTHER documents
                cross_results = await rag_service.search_documents(
                    query=request.message,
                    top_k=3,
                    exclude_document_id=request.document_id,
                    user_id=user_id,
                    llm_provider=None,
                    use_advanced_rag=False
                )

                doc_name_cache = {}
                try:
                    all_docs = db.get_all_documents(client_id=user_id)
                    for doc in all_docs:
                        doc_name_cache[doc.id] = _document_display_name(doc)
                except:
                    pass

                for result in cross_results:
                    formatted = format_retrieval_result(result, snippet_chars=150)
                    cross_doc_suggestions.append({
                        'document_id': formatted.get('document_id'),
                        'document_name': doc_name_cache.get(
                            formatted.get('document_id'),
                            formatted.get('document_name', 'Document'),
                        ),
                        'page_number': formatted.get('page_number') or 1,
                        'text': formatted.get('text', ''),
                        'similarity': formatted.get('similarity', 0.0),
                        'vector_similarity': formatted.get('vector_similarity', 0.0),
                        'retrieval_score': formatted.get('retrieval_score'),
                    })
            except Exception as e:
                print(f"⚠️ Could not fetch cross-document suggestions: {e}")

            # Save assistant message to history
            await chat_mgr.save_message(
                user_id=user_id,
                session_id=session_id,
                role="assistant",
                content=response_text,
                metadata={'sources': sources, 'context_type': 'pdf_viewer'}
            )
            
            return {
                "response": response_text,
                "sources": sources,
                "context": context,
                "has_context": True,
                "success": True,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "related_documents": cross_doc_suggestions  # Cross-document related content
            }
            
        else:
            # Library context
            print(f"📚 Building library context for user: {user_id}")
            context = await build_library_context(db=db, user_id=user_id)
            print("✅ Library context built")
            
            if os.getenv("DEBUG_CHAT_LOGGING", "false").lower() == "true":
                with open("backend_debug.log", "a", encoding="utf-8") as f:
                    f.write(f"Library Context Stats: {context.get('statistics')}\n")
                    f.write(f"Doc Summaries: {len(context.get('document_summaries', []))}\n")
            
            # NEW: Perform library-wide search for relevant content
            print("🔍 Searching library documents...")
            search_results = await search_library_documents(
                query_text=request.message,
                user_id=user_id,
                top_k=5
            )
            print(f"✅ Search completed. Found {len(search_results)} results")
            
            # Add search results to context
            if search_results:
                context['search_results'] = search_results
            
            # Build enriched messages with library context
            enriched_messages = build_enriched_messages(
                user_message=request.message,
                context=context,
                conversation_history=request.conversation_history or []
            )
            
            # Get LLM response
            print("🤖 Calling LLM (via LangChain Provider)...")
            # Uses the globally initialized llm_provider which has LangChain + Fallback
            response_text = await llm_provider.generate_chat_response(enriched_messages)
            print("✅ LLM response received")
            
            # Save assistant message to history
            await chat_mgr.save_message(
                user_id=user_id,
                session_id=session_id,
                role="assistant",
                content=response_text,
                metadata={'search_results': search_results, 'context_type': 'library'}
            )
            
            return {
                "response": response_text,
                "context": context,
                "has_context": True,
                "success": True,
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
    
    except HTTPException:
        raise
    except Exception:
        logger.exception("Chat endpoint error")
        return {
            "response": "I apologize, but I encountered an error processing your request.",
            "success": False,
            "timestamp": datetime.now().isoformat()
        }


# RAG endpoints
@app.post("/api/rag/process/{document_id}")
async def process_document_for_rag(document_id: str, current_user: dict = Depends(get_current_user)):
    """
    Process a single document for RAG
    Chunks, embeds, and stores in vector database
    """
    try:
        from .rag_service import get_rag_service
        rag_service = get_rag_service()
        user_id = current_user["sub"]

        document = db.get_document_by_id(document_id, client_id=user_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        existing_chunks = db.get_chunk_count(document_id=document_id, client_id=user_id)

        if existing_chunks > 0:
            return {
                "success": True,
                "document_id": document_id,
                "message": "Document already processed",
                "chunks_existing": existing_chunks,
            }

        file_path = Path(document.file_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Document file not found")

        return await rag_service.process_document(
            document_id=document.id,
            pdf_path=str(file_path),
            user_id=user_id,
            mode="single",
            batch_size=32
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error processing all documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/rag/document/{document_id}")
async def delete_document_from_rag(document_id: str, current_user: dict = Depends(get_current_user)):
    """Remove document from RAG system"""
    try:
        from .rag_service import get_rag_service
        rag_service = get_rag_service()
        user_id = current_user["sub"]

        document = db.get_document_by_id(document_id, client_id=user_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        result = rag_service.delete_document_from_rag(document_id, user_id=user_id)
        return result

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error deleting document from RAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Catch-all route for SPA routing (MUST be last)
# Absolute, so it does not depend on the process working directory.
FRONTEND_DIST_DIR = BACKEND_DIR.parent / "frontend" / "dist"
_STATIC_MEDIA_TYPES = {
    ".js": "application/javascript",
    ".css": "text/css",
    ".html": "text/html",
    ".json": "application/json",
    ".svg": "image/svg+xml",
}


@app.get("/{path:path}")
async def serve_frontend(path: str):
    """Serve React app for all routes (SPA routing)"""
    # Unknown API paths must 404, not return the SPA shell with a 200.
    if path == "api" or path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not Found")

    dist_root = FRONTEND_DIST_DIR.resolve()
    static_file = (dist_root / path).resolve()
    # Only serve files that stay inside the build folder (blocks ../ traversal).
    if static_file.is_relative_to(dist_root) and static_file.is_file():
        return FileResponse(static_file, media_type=_STATIC_MEDIA_TYPES.get(static_file.suffix.lower()))

    # For all other routes, serve the React app (SPA routing)
    return await get_frontend()


print("✅✅✅ APPLICATION MODULE LOADED SUCCESSFULLY ✅✅✅")
print("🎉 Ready to accept connections!")
sys.stdout.flush()
