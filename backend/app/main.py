import sys # trigger reload 2
import traceback

with open("main_heartbeat.txt", "w") as f:
    f.write("main_loaded")

print("🚀 Starting application import...")
sys.stdout.flush()

try:
    import asyncio
    import uuid
    from pathlib import Path
    from typing import List, Dict, Any, Optional
    from fastapi import FastAPI, UploadFile, File, BackgroundTasks, WebSocket, WebSocketDisconnect, HTTPException, Query, Request, Depends
    from pydantic import BaseModel
    from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
    from fastapi.staticfiles import StaticFiles
    from fastapi.middleware.cors import CORSMiddleware
    import os
    import shutil
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
print("✅ Websocket and models loaded")
sys.stdout.flush()

# Database selection: Use Supabase if configured, otherwise SQLite
# Database selection: Supabase Only
USE_SUPABASE = True
print("🗄️ Database mode: Supabase Only")
sys.stdout.flush()

try:
    from .supabase_database import get_supabase_db
    db = get_supabase_db()
    from .api_routes_supabase import router as api_router
    from .auth_middleware import get_current_user, get_optional_user
    print("✅ Using Supabase database with authentication")
except Exception as e:
    print(f"❌ FATAL: Failed to initialize Supabase: {e}")
    sys.stdout.flush()
    raise

print("📦 Loading services...")
sys.stdout.flush()
from .pdf_comparator import pdf_comparator
from .llm_providers import get_llm_provider
from .enhanced_llm_service import EnhancedLLMService
from .tts_service import TTSService
from .section_highlighter import SectionHighlighter
from .duplicate_cleaner import run_duplicate_cleanup
from .smart_upload_handler import SmartUploadHandler
print("✅ Services loaded")
sys.stdout.flush()

print("📦 Loading PDF processors...")
sys.stdout.flush()
from app.utils.process_pdfs import HighPerformancePDFProcessor  # 1A outline extraction
from app.utils.intelligent_pdf_brain import IntelligentPDFBrain  # 1B relevance/insights
print("✅ PDF processors loaded")
sys.stdout.flush()

print("📦 Loading RAG Service...")
sys.stdout.flush()
from .rag_service import get_rag_service
print("✅ RAG Service loaded")
sys.stdout.flush()

# Create necessary directories - use consistent paths
print("📁 Setting up directories...")
sys.stdout.flush()
BACKEND_DIR = Path(__file__).parent.parent  # Go up from app/ to backend/
DATA_DIR = BACKEND_DIR / "data"
DOCS_DIR = DATA_DIR / "docs"
DOCS_DIR.mkdir(parents=True, exist_ok=True)

print(f"📁 Backend directory: {BACKEND_DIR}")
print(f"📁 Data directory: {DATA_DIR}")
print(f"📁 Docs directory: {DOCS_DIR}")
sys.stdout.flush()

print("🚀 Creating FastAPI app...")
sys.stdout.flush()
app = FastAPI(title="Adobe Hackathon Grand Finale Backend")
print("✅ FastAPI app created")
sys.stdout.flush()

# Add CORS middleware FIRST
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
# Initialize services
llm_provider = None
try:
    import importlib
    import app.llm_providers as app_llm_providers
    importlib.reload(app_llm_providers)
    print("🔄 Reloaded llm_providers module")
    
    from .llm_providers import get_llm_provider
    llm_provider = get_llm_provider()
    print(f"✅ LLM Provider initialized: {type(llm_provider).__name__}")
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

try:
    tts_service = TTSService()
    print(f"✅ TTS Service initialized")
except Exception as e:
    print(f"⚠️ TTS Service initialization failed: {e}")

print(f"✅ Section Highlighter initialized")

# Initialize smart upload handler
# SQLite maintenance tasks removed

# Enhanced PDF processing function with better integration
async def process_pdf(job_id: str, client_id: str, file_path: str, pdf_type: str, persona: str = None, job: str = None):
    print(f"Processing {pdf_type} job {job_id} for client {client_id}")

    try:
        # WS Progress: Start
        await manager.send_message({
            "type": "progress",
            "job_id": job_id,
            "data": {"percent": 10, "message": "Starting PDF extraction..."}
        }, client_id)

        # 1A: Extract outline (headings, pages, text)
        processor = HighPerformancePDFProcessor()
        result = processor.process_single_pdf(Path(file_path), Path('data'))
        outline = result.get('outline', [])

        await manager.send_message({
            "type": "progress",
            "job_id": job_id,
            "data": {"percent": 30, "message": f"Extracted {len(outline)} sections"}
        }, client_id)

        # Enhanced embedding and FAISS indexing
        from .vector_store import get_vector_store
        from .embedding_service import get_embedding_service
        vector_store = get_vector_store()
        embedding_service = get_embedding_service()

        sections_added = 0
        for sec in outline:
            try:
                sec_id = str(uuid.uuid4())
                # Create more comprehensive text for embedding
                section_text = f"{sec.get('heading', '')} {sec.get('text', '')}"

                if section_text.strip():  # Only process non-empty sections
                    embedding = embedding_service.generate_embedding(section_text)
                    vector_store.index.add(np.array([embedding]).astype('float32'))
                    # Also store metadata
                    vector_store.metadata.append({
                        'id': sec_id,
                        'doc_id': job_id,
                        'heading': sec.get('heading', ''),
                        'text': sec.get('text', ''),
                        'page': sec.get('page', 1),
                        'user_id': client_id
                    })

                    # Store in Supabase if enabled
                    try:
                        db.store_chunk(
                            user_id=client_id,
                            document_id=job_id,
                            chunk_text=section_text,
                            chunk_index=sections_added,
                            page_number=sec.get('page', 1),
                            embedding=embedding.tolist(),
                            char_count=len(section_text),
                            word_count=len(section_text.split())
                        )
                    except Exception as e:
                        print(f"⚠️ Failed to store chunk in Supabase: {e}")

                    sections_added += 1
            except Exception as e:
                print(f"Error processing section: {e}")
                continue

        # Save the FAISS index after processing
        vector_store.save()

        await manager.send_message({
            "type": "progress",
            "job_id": job_id,
            "data": {"percent": 60, "message": f"Indexed {sections_added} sections"}
        }, client_id)

        # 1B: Enhanced relevance and insights processing
        insights = []
        relevance_data = []

        if persona and job and llm_provider:
            try:
                # Use LLM for better insights
                content_summary = " ".join([sec.get('text', '')[:200] for sec in outline[:5]])  # First 5 sections
                insights = await llm_provider.generate_insights(content_summary, persona, job)

                await manager.send_message({
                    "type": "insights",
                    "job_id": job_id,
                    "data": insights
                }, client_id)

            except Exception as e:
                print(f"Error generating insights: {e}")
                # Fallback to 1B brain
                try:
                    brain = IntelligentPDFBrain()
                    temp_collection_path = Path('data/temp_collection')
                    temp_collection_path.mkdir(exist_ok=True)
                    shutil.copy(file_path, temp_collection_path / Path(file_path).name)
                    insights = brain.process_collection_intelligently(temp_collection_path)
                    shutil.rmtree(temp_collection_path)
                except Exception as brain_error:
                    print(f"Error with 1B brain: {brain_error}")

        await manager.send_message({
            "type": "progress",
            "job_id": job_id,
            "data": {"percent": 90, "message": "Finalizing processing..."}
        }, client_id)

        # Prepare final data
        final_data = {
            "outline": outline,
            "insights": insights,
            "sections_indexed": sections_added,
            "pdf_type": pdf_type,
            "persona": persona,
            "job": job
        }

        # Final WS message
        await manager.send_message({
            "type": "complete",
            "job_id": job_id,
            "data": {
                "percent": 100,
                "message": "Processing Complete!",
                "result": final_data
            }
        }, client_id)

        print(f"✅ Finished processing job {job_id}: {sections_added} sections indexed")

    except Exception as e:
        print(f"❌ Error processing job {job_id}: {e}")
        await manager.send_message({
            "type": "error",
            "job_id": job_id,
            "data": {"message": f"Processing failed: {str(e)}"}
        }, client_id)

# --- API Endpoints ---

# NEW: Endpoint for PAST/CONTEXT PDFs (bulk upload)
@app.post("/upload/context_files")
async def upload_context_files(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    persona: str = None,
    job: str = None,
    current_user: Optional[dict] = Depends(get_optional_user),
    client_id: Optional[str] = Query(None, description="User identifier for multi-tenant uploads")
):
    """
    Accepts multiple PDF files to add to the knowledge base (Supabase or SQLite).
    """
    uploaded_files_info = []
    user_id = client_id or (current_user.get("sub") if current_user else "local-user")
    
    print(f"📚 Uploading {len(files)} context files for user {user_id}")
    sys.stdout.flush()

    for file in files:
        try:
            job_id = str(uuid.uuid4())
            filename_with_id = f"{job_id}_{file.filename}"
            file_path = DOCS_DIR / filename_with_id
            
            # Save file
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
                
            # Create DB Record
            # Create DB Record
            doc = db.create_document(
                user_id=user_id,
                filename=filename_with_id,
                original_name=file.filename,
                file_size=len(content),
                file_path=str(file_path),
                persona=persona,
                job_role=job
            )
            job_id = doc.id
            
            # Add to background tasks
            # Use 'library' context for bulk uploads
            background_tasks.add_task(process_pdf, job_id, user_id, str(file_path), 'library', persona, job)
            
            uploaded_files_info.append({
                "job_id": job_id,
                "filename": file.filename,
                "status": "uploading"
            })
            print(f"✅ Queued file for processing: {file.filename} (ID: {job_id})")
            
        except Exception as e:
            print(f"❌ Failed to upload {file.filename}: {e}")
            uploaded_files_info.append({
                "filename": file.filename,
                "error": str(e),
                "status": "failed"
            })
            # Cleanup
            try:
                if 'file_path' in locals() and file_path.exists():
                    file_path.unlink()
            except:
                pass

    return JSONResponse(
        status_code=202,
        content={
            "detail": f"Processing {len(files)} files",
            "files": uploaded_files_info
        }
    )
# NEW: Endpoint for CURRENT PDF (for viewing)
@app.post("/upload/active_file")
async def upload_active_file(
    background_tasks: BackgroundTasks,
    persona: str = None,
    job: str = None,
    file: UploadFile = File(...),
    current_user: Optional[dict] = Depends(get_optional_user),
    client_id: Optional[str] = Query(None, description="User identifier for multi-tenant uploads")
):
    """
    Accepts a single "current" PDF for immediate viewing and analysis.
    """
    user_id = client_id or (current_user.get("sub") if current_user else "local-user")
    job_id = str(uuid.uuid4())
    filename_with_id = f"{job_id}_{file.filename}"
    file_path = DOCS_DIR / filename_with_id

    # Save the uploaded file temporarily
    file_content = await file.read()
    with open(file_path, "wb") as buffer:
        buffer.write(file_content)

    # Use smart upload handler for duplicate detection and processing
    if 'smart_upload_handler' in globals() and smart_upload_handler:
        try:
            print(f"📚 Processing upload with smart handler: {file.filename}")

            upload_result = smart_upload_handler.handle_upload(
                file_path, file.filename, user_id, persona, job
            )

            if upload_result['is_duplicate']:
                print(f"🔄 Duplicate detected: {file.filename}")
                existing_doc = upload_result['existing_document']

                # Remove temporary file since we're using existing one
                if file_path.exists():
                    file_path.unlink()

                # Return existing document info
                return JSONResponse(
                    status_code=200,
                    content={
                        "job_id": existing_doc['id'],
                        "filename": file.filename,
                        "detail": f"File already exists. Updated access time for existing document.",
                        "file_url": f"/api/files/{existing_doc['filename']}",
                        "is_duplicate": True,
                        "original_upload_date": existing_doc['upload_date']
                    }
                )
            else:
                print(f"✅ New file processed: {file.filename}")
                job_id = upload_result['document_id']
                filename_with_id = upload_result['filename']

                # Remove temporary file since smart handler already processed it
                if file_path.exists():
                    file_path.unlink()
                    print(f"🗑️ Removed temporary file: {file_path.name}")

                print(f"✅ New document processed successfully: {filename_with_id}")

                # Verify it was stored
                if USE_SUPABASE:
                    # For Supabase, we might need to check differently or trust it worked
                    pass
                else:
                    all_docs = db.get_all_documents(client_id=user_id)
                    print(f"📊 Total documents in database after upload: {len(all_docs)}")

        except Exception as e:
            print(f"⚠️ Smart upload handler failed: {e}")
            raise e
    else:
        # Fallback: Direct upload without smart handler (for Supabase or when handler missing)
        print(f"ℹ️ Smart upload handler not available, processing directly: {file.filename}")
        
        try:
            # Create document record in DB
            if USE_SUPABASE:
                doc = db.create_document(
                    user_id=user_id,
                    filename=filename_with_id,
                    original_name=file.filename,
                    file_size=len(file_content),
                    file_path=str(file_path),
                    persona=persona,
                    job_role=job
                )
                job_id = doc.id
            else:
                doc = db.create_document(
                    filename=filename_with_id,
                    original_name=file.filename,
                    file_size=len(file_content),
                    file_path=str(file_path),
                    client_id=user_id,
                    persona=persona,
                    job_role=job
                )
                job_id = doc.id
                
            print(f"✅ New document created directly: {job_id}")
            
        except Exception as e:
            print(f"❌ Failed to create document record: {e}")
            if file_path.exists():
                file_path.unlink()
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

        # Start the background processing task for this file
        actual_file_path = DOCS_DIR / filename_with_id
        background_tasks.add_task(process_pdf, job_id, user_id, str(actual_file_path), 'current', persona, job)

        return JSONResponse(
            status_code=202,
            content={
                "job_id": job_id,
                "filename": file.filename,
                "detail": "Active file accepted for viewing and processing.",
                "file_url": f"/api/files/{filename_with_id}"
            }
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


@app.get("/api/recommendations/{document_id}")
async def get_recommendations(
    document_id: str,
    page: int = Query(1, ge=1),
    persona: str = Query(None),
    job: str = Query(None),
    include_cross_document: bool = Query(True, description="Include cross-document recommendations")
):
    """Get related sections for a specific document and page with intelligent cross-document connections"""
    try:
        # Import vector store and embedding service
        import numpy as np
        from .vector_store import get_vector_store
        from .embedding_service import get_embedding_service

        vector_store = get_vector_store()
        embedding_service = get_embedding_service()

        # Query FAISS index for similar sections
        if vector_store.index.ntotal == 0:
            return {"recommendations": [], "cross_document_sections": []}

        # Build a cache of document names from database
        doc_name_cache = {}
        try:
            all_docs = db.get_all_documents()
            for doc in all_docs:
                doc_name_cache[doc.id] = doc.original_name or doc.filename or f"Document {doc.id[:8]}"
        except Exception as e:
            print(f"⚠️ Could not fetch document names: {e}")

        # Get current page content (simplified - in production, extract actual page content)
        current_content = f"Page {page} content for document {document_id}"

        # Enhanced query with persona and job context
        if persona and job:
            current_content += f" Context: {persona} working on {job}"

        # Encode query
        query_embedding = embedding_service.generate_embedding(current_content)

        # Search FAISS index for semantic similarity
        k = min(10, vector_store.index.ntotal)  # Get top 10 candidates
        distances, indices = vector_store.index.search(np.array([query_embedding]).astype('float32'), k)

        # Separate same-document and cross-document recommendations
        same_document_recommendations = []
        cross_document_recommendations = []

        # Track unique documents for cross-document intelligence
        document_texts = {}

        for i, idx in enumerate(indices[0]):
            if idx < len(vector_store.metadata):
                meta = vector_store.metadata[idx]
                relevance = float(1.0 - distances[0][i])

                # Skip very low relevance matches
                if relevance < 0.3:
                    continue

                # Get actual document name from cache or fallback
                doc_id = meta['doc_id']
                doc_name = doc_name_cache.get(doc_id, meta.get('filename', f"Document {doc_id[:8]}..."))

                recommendation = {
                    "id": meta['id'],
                    "title": meta['heading'],
                    "snippet": meta['text'][:200] + "..." if len(meta['text']) > 200 else meta['text'],
                    "page": meta['page'],
                    "relevance": relevance,
                    "documentId": meta['doc_id'],
                    "documentName": doc_name,
                    "bbox": None,  # Will be populated by highlighting system
                    "file_path": meta.get('file_path', '')
                }
                
                if meta['doc_id'] == document_id:
                    same_document_recommendations.append(recommendation)
                else:
                    cross_document_recommendations.append(recommendation)
                    # Store document content for intelligent analysis
                    if meta['doc_id'] not in document_texts:
                        document_texts[meta['doc_id']] = []
                    document_texts[meta['doc_id']].append(meta['text'])

        # Enhanced cross-document intelligence using the intelligent PDF brain
        enhanced_cross_document = []
        if include_cross_document and cross_document_recommendations and persona and job:
            try:
                # Initialize the intelligent PDF brain
                from app.utils.intelligent_pdf_brain import IntelligentPDFBrain
                brain = IntelligentPDFBrain()
                
                # Score cross-document sections using intelligent analysis
                for rec in cross_document_recommendations[:5]:  # Limit to top 5 for processing
                    # Create a simple section-like object for scoring
                    class SimpleSection:
                        def __init__(self, content):
                            self.content = content
                            self.section_title = rec['title']
                            self.page_number = rec['page']
                    
                    section = SimpleSection(rec['snippet'])
                    
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
        
        # Return top 3 same-document and top 3 cross-document recommendations
        result = {
            "recommendations": same_document_recommendations[:3],
            "cross_document_sections": enhanced_cross_document[:3] if include_cross_document else [],
            "total_found": len(same_document_recommendations) + len(cross_document_recommendations),
            "intelligence_enabled": include_cross_document and persona and job
        }
        
        print(f"📊 Recommendations for {document_id} page {page}: {len(result['recommendations'])} same-doc, {len(result['cross_document_sections'])} cross-doc")
        
        return result

    except Exception as e:
        print(f"Error getting recommendations: {e}")
        return {"recommendations": [], "cross_document_sections": [], "error": str(e)}


@app.get("/api/insights/{document_id}")
async def get_insights(
    document_id: str,
    page: int = Query(1, ge=1),
    persona: str = Query(None),
    job: str = Query(None)
):
    """Generate comprehensive AI-powered insights for a specific document and page using actual PDF content"""
    try:
        if not enhanced_llm_service:
            print("⚠️ Enhanced LLM service not available, returning mock insights for testing")
            # Return mock insights for testing when LLM is not available
            mock_insights = [
                {
                    "id": "1",
                    "type": "key-insight",
                    "title": "Core Concept",
                    "content": "This section introduces fundamental concepts that form the foundation for understanding the broader topic.",
                    "relevance": 0.9
                },
                {
                    "id": "2",
                    "type": "did-you-know", 
                    "title": "Background Context",
                    "content": "Research shows that understanding these principles can improve comprehension by up to 40% compared to linear reading.",
                    "relevance": 0.8
                },
                {
                    "id": "3",
                    "type": "counterpoint",
                    "title": "Alternative Perspective",
                    "content": "While this approach is widely accepted, some experts argue for a more nuanced interpretation of the data.",
                    "relevance": 0.7
                },
                {
                    "id": "4",
                    "type": "connection",
                    "title": "Related Concepts",
                    "content": "This content connects to similar themes found in related documents and industry best practices.",
                    "relevance": 0.8
                }
            ]
            return {"insights": mock_insights, "mock": True}

        # Get the actual document from database
        document = db.get_document_by_id(document_id)
        if not document:
            return {"insights": [], "error": "Document not found"}

        # Extract FULL PDF content for comprehensive AI analysis
        page_content = ""
        full_pdf_content = ""

        # Import vector store for fallback content retrieval
        from .vector_store import get_vector_store
        vector_store = get_vector_store()

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

            if pdf_path.exists():
                pdf_doc = fitz.open(pdf_path)
                total_pages = len(pdf_doc)
                
                # Extract content from ALL pages for comprehensive analysis
                all_pages_content = []
                for page_num in range(total_pages):
                    page_text = pdf_doc[page_num].get_text()
                    if page_text.strip():  # Only add non-empty pages
                        all_pages_content.append(f"=== Page {page_num + 1} ===\n{page_text}")
                
                # Get current page content specifically
                if page <= total_pages:
                    current_page = pdf_doc[page - 1]
                    page_content = current_page.get_text()
                
                # Combine all content with current page highlighted
                full_pdf_content = "\n\n".join(all_pages_content)
                
                # Create comprehensive content for LLM analysis
                full_content = f"""DOCUMENT: {document.original_name}
TOTAL PAGES: {total_pages}
CURRENT PAGE FOCUS: {page}

CURRENT PAGE CONTENT:
{page_content}

COMPLETE DOCUMENT CONTENT:
{full_pdf_content[:15000]}{'...' if len(full_pdf_content) > 15000 else ''}"""
                
                pdf_doc.close()
                print(f"📄 Extracted full PDF: {total_pages} pages, {len(full_pdf_content)} characters total")
            else:
                print(f"⚠️ PDF file not found: {pdf_path}")
                # Fallback: try to get content from FAISS metadata
                matching_sections = [meta for meta in vector_store.metadata if meta.get('doc_id') == document_id]
                if matching_sections:
                    page_content = "\n".join([meta.get('text', '') for meta in matching_sections if meta.get('page') == page])
                    full_content = f"Page {page} Content:\n{page_content}"
                else:
                    full_content = f"Document {document.original_name}, Page {page} - Content extraction failed"
            
        except Exception as e:
            print(f"Error extracting PDF content: {e}")
            # Fallback to FAISS metadata if PDF extraction fails
            matching_sections = [meta for meta in metadata if meta.get('doc_id') == document_id]
            if matching_sections:
                page_content = "\n".join([meta.get('text', '') for meta in matching_sections if meta.get('page') == page])
                full_content = f"Page {page} Content:\n{page_content}"
            else:
                full_content = f"Document: {document.original_name}, Page {page} - Unable to extract content"

                # Generate comprehensive insights using LLM with ACTUAL PDF FILE (multimodal analysis)
        print(f"🧠 Generating comprehensive insights for {document.original_name}")
        print(f"📊 PDF file: {document.file_path}")
        print(f"📄 Page focus: {page}, Full document analysis: enabled")
        
        # Get related sections for context
        related_sections = []
        try:
            # Get related sections from the same document and others
            all_documents = db.get_all_documents(client_id=user_id)
            for doc in all_documents[:3]:  # Limit to 3 documents for context
                if doc.id != document_id:  # Skip current document
                    doc_metadata = db.get_document_metadata(doc.id)
                    if doc_metadata:
                        # Get a sample section from each document
                        for meta in doc_metadata[:2]:  # Max 2 sections per document
                            related_sections.append({
                                'title': f"{doc.original_name} - Page {meta.get('page', 1)}",
                                'snippet': meta.get('text', '')[:200] + '...' if len(meta.get('text', '')) > 200 else meta.get('text', ''),
                                'document_id': doc.id,
                                'page': meta.get('page', 1)
                            })
        except Exception as e:
            print(f"Warning: Could not get related sections: {e}")

        try:
            # Use Enhanced LLM Service for AI insights generation
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
            
        except Exception as llm_error:
            print(f"❌ LLM failed to generate insights: {llm_error}")
            print(f"🔍 Error type: {type(llm_error).__name__}")
            if "credentials" in str(llm_error).lower():
                print("🔐 Credential issue detected - check GOOGLE_APPLICATION_CREDENTIALS")
            elif "quota" in str(llm_error).lower():
                print("💸 API quota issue detected")
            elif "permission" in str(llm_error).lower():
                print("🚫 Permission issue detected")
            print("🔄 Generating content-aware insights based on extracted PDF text...")
            
            # Generate content-aware insights based on the actual PDF content
            content_preview = full_content[:300] + "..." if len(full_content) > 300 else full_content
            
            # Create better fallback insights based on actual content
            content_length = len(full_pdf_content) if 'full_pdf_content' in locals() else len(full_content)
            
            insights = [
                {
                    "id": "1",
                    "type": "key-insight",
                    "title": f"Document Analysis: {document.original_name}",
                    "content": f"This document contains comprehensive content across multiple sections, with focus on page {page} providing key information.",
                    "relevance": 0.9
                },
                {
                    "id": "2",
                    "type": "did-you-know",
                    "title": "Content Metrics",
                    "content": f"This PDF has {content_length // 1000}k+ characters of extractable content, indicating rich information density.",
                    "relevance": 0.8
                },
                {
                    "id": "3",
                    "type": "counterpoint",
                    "title": "Processing Status",
                    "content": f"Content successfully extracted and analyzed - AI processing available with proper LLM configuration.",
                    "relevance": 0.7
                },
                {
                    "id": "4",
                    "type": "connection",
                    "title": "Document Accessibility",
                    "content": f"Full document content processed for comprehensive analysis with page {page} as primary focus.",
                    "relevance": 0.8
                }
            ]
            
            print(f"✅ Generated content-aware insights based on extracted PDF text")
            return {"insights": insights, "content_based": True, "llm_error": str(llm_error)}

    except Exception as e:
        print(f"❌ Error generating insights: {e}")
        import traceback
        traceback.print_exc()
        return {"insights": [], "error": str(e)}


@app.post("/api/generate-podcast")
async def generate_podcast(request: Request):
    """Generate a podcast-style audio overview with Azure TTS"""
    try:
        if not tts_service:
            raise HTTPException(status_code=503, detail="TTS service not available")

        # Parse request body
        body = await request.json()
        document_id = body.get("document_id")
        page = body.get("page", 1)
        selected_text = body.get("selected_text")
        persona = body.get("persona")
        job = body.get("job")

        print(f"🎙️ Generating podcast for document {document_id}, page {page}")
        print(f"📝 Selected text: {selected_text[:100] if selected_text else 'None'}...")

        # Determine content source
        if selected_text and len(selected_text.strip()) > 10:
            # Use selected text
            content = selected_text.strip()
            title = f"Selected Text from {document_id}"
            print(f"🎯 Using selected text ({len(content)} chars)")
        else:
            # Try to get actual document content
            try:
                # Get document from database
                doc = db.get_document_by_id(document_id)
                if doc:
                    # Try to extract content from the PDF
                    pdf_path = Path(doc.file_path)
                    if pdf_path.exists():
                        import PyPDF2
                        with open(pdf_path, 'rb') as file:
                            pdf_reader = PyPDF2.PdfReader(file)
                            if page <= len(pdf_reader.pages):
                                page_content = pdf_reader.pages[page - 1].extract_text()
                                content = page_content[:2000]  # Limit for reasonable audio length
                                title = f"{doc.original_name} - Page {page}"
                                print(f"📄 Using PDF content ({len(content)} chars)")
                            else:
                                content = f"Content from page {page} of {doc.original_name}"
                                title = f"{doc.original_name} - Page {page}"
                    else:
                        content = f"Document content from {doc.original_name}, page {page}"
                        title = f"{doc.original_name} - Page {page}"
                else:
                    content = f"Document content from page {page}"
                    title = f"Document - Page {page}"
            except Exception as e:
                print(f"⚠️ Could not extract PDF content: {e}")
                # Use a more descriptive fallback content
                content = f"Welcome to your document analysis. This is page {page} of your PDF document. The system is ready to provide insights and analysis of your content."
                title = f"Document Analysis - Page {page}"

        # Add persona context
        if persona and job:
            content = f"As a {persona} working on {job}, here's what you need to know: {content}"

        # Generate audio using Azure TTS (now with proper audio_config)
        print(f"🔊 Generating audio with Azure TTS...")
        try:
            audio_data = await tts_service.generate_podcast(content, title)

            # Save to temporary file
            filename = f"podcast_{document_id}_{page}_{hash(content) % 10000}.wav"
            audio_file = await tts_service.save_audio_file(audio_data, filename)

            print(f"✅ Podcast generated: {audio_file}")
            return {"audioUrl": f"/api/audio/{Path(audio_file).name}"}

        except Exception as tts_error:
            print(f"⚠️ Azure TTS failed: {tts_error}")
            print(f"🔄 Using demo audio as fallback...")

            # Fallback to demo audio for hackathon
            return {
                "audioUrl": "/api/audio/demo_podcast.mp3",
                "title": title,
                "content_length": len(content),
                "status": "fallback_demo",
                "message": f"Using demo audio - Azure TTS error: {str(tts_error)}"
            }

    except Exception as e:
        print(f"❌ Error generating podcast: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Old endpoints removed - now using proper API routes in api_routes.py

@app.get("/api/files/{filename}")
@app.head("/api/files/{filename}")
async def get_pdf_file(filename: str):
    """Serve uploaded PDF files for PDF.js and Adobe PDF Embed API with proper CORS headers"""
    file_path = DOCS_DIR / filename
    if file_path.exists():
        return FileResponse(
            file_path,
            media_type="application/pdf",
            headers={
                "Accept-Ranges": "bytes",
                "Cache-Control": "public, max-age=3600",
                "Content-Disposition": f"inline; filename={filename}",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
                "Access-Control-Allow-Headers": "*",
                "Cross-Origin-Resource-Policy": "cross-origin",
                "Cross-Origin-Embedder-Policy": "unsafe-none"
            }
        )
    else:
        raise HTTPException(status_code=404, detail="PDF file not found")


@app.get("/api/audio/{filename}")
async def get_audio(filename: str):
    """Serve generated audio files with proper headers for web playback"""
    # Check temp_audio directory first (for generated files)
    audio_path = DATA_DIR / "temp_audio" / filename
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

    # Check demo audio directory (for demo files)
    demo_audio_path = DATA_DIR / "audio" / filename
    if demo_audio_path.exists():
        media_type = "audio/wav" if filename.endswith('.wav') else "audio/mpeg"
        return FileResponse(
            demo_audio_path,
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
        
        # Get current document context
        # Pass user_id if using Supabase
        if USE_SUPABASE:
             current_doc = db.get_document_by_id(request.document_id, user_id)
        else:
             # Should not happen in Supabase only mode
             current_doc = None
            
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
                    # Fetch document name if missing (SearchResult might not have it if not in metadata)
                    doc_name = "Unknown Document"
                    if res.metadata and 'document_name' in res.metadata:
                        doc_name = res.metadata['document_name']
                    elif res.document_id == request.document_id:
                        doc_name = current_doc.original_name
                    
                    candidate_sections.append({
                        "section_id": i,
                        "document_id": res.document_id,
                        "document_name": doc_name,
                        "title": res.metadata.get("section_title", "Untitled") if res.metadata else "Untitled",
                        "content": res.chunk_text,
                        "page": res.page_number,
                        "faiss_score": res.similarity_score
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

        # Get document
        if USE_SUPABASE:
            document = db.get_document_by_id(document_id, user_id)
        else:
             # Should not happen
            document = None
            
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


@app.post("/api/generate-podcast")
async def generate_podcast(
    content: str,
    document_id: str,
    page: int = 1,
    persona: str = None,
    job: str = None,
    include_related: bool = True
):
    """
    Bonus Feature: Generate podcast from content (+5 points)
    Creates 2-speaker conversational audio overview
    """
    try:
        if not enhanced_llm_service:
            raise HTTPException(status_code=503, detail="Enhanced LLM service not available")

        # Get related sections if requested
        related_sections = []
        if include_related:
            try:
                import numpy as np
                from .vector_store import get_vector_store
                from .embedding_service import get_embedding_service

                vector_store = get_vector_store()
                embedding_service = get_embedding_service()

                if vector_store.index.ntotal > 0:
                    query_embedding = embedding_service.generate_embedding(content[:500])  # Use first 500 chars

                    k = min(5, vector_store.index.ntotal)
                    distances, indices = vector_store.index.search(np.array([query_embedding]).astype('float32'), k)

                    for i, idx in enumerate(indices[0]):
                        if idx < len(vector_store.metadata):
                            section_data = vector_store.metadata[idx]
                            related_sections.append({
                                "title": section_data.get("section_title", section_data.get("heading", "Section")),
                                "content": section_data.get("text", "")[:200],
                                "document_name": section_data.get("document_name", "Document")
                            })
            except Exception as e:
                print(f"Error getting related sections for podcast: {e}")

        # Generate insights for podcast content
        insights = await enhanced_llm_service.generate_insights_bulb(
            content, related_sections, persona, job
        )

        # Generate podcast script
        script = await enhanced_llm_service.generate_podcast_script(
            content, related_sections, insights, persona, job
        )

        # Generate audio (for now, return script - audio generation can be done client-side)
        # In production, would generate actual audio file
        audio_file = None
        try:
            audio_file = await enhanced_llm_service.generate_podcast_audio(script)
        except Exception as e:
            print(f"Audio generation failed, returning script only: {e}")

        return {
            "script": script,
            "audio_file": audio_file,
            "insights": insights,
            "related_sections": related_sections,
            "metadata": {
                "document_id": document_id,
                "page": page,
                "persona": persona,
                "job": job,
                "duration_estimate": script.get("duration_estimate", "3-4 minutes")
            }
        }

    except Exception as e:
        print(f"Error generating podcast: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/highlights/{document_id}")
async def get_section_highlights(
    document_id: str,
    page: int = Query(1, ge=1)
):
    """Get section highlighting data for PDF overlay"""
    try:
        # First get recommendations for this page
        recommendations_response = await get_recommendations(document_id, page)
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
async def split_document(request: Request):
    """Split a PDF document into multiple PDFs based on page ranges"""
    try:
        body = await request.json()
        document_id = body.get("document_id")
        splits = body.get("splits", [])  # List of {name, start_page, end_page}

        if not document_id:
            raise HTTPException(status_code=400, detail="Document ID is required")

        if len(splits) < 2:
            raise HTTPException(status_code=400, detail="At least 2 splits required")

        print(f"✂️ Splitting document {document_id} into {len(splits)} parts")

        # Get document from database
        document = db.get_document_by_id(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        # Verify PDF file exists
        pdf_path = Path(document.file_path)
        if not pdf_path.exists():
            raise HTTPException(status_code=404, detail=f"PDF file not found: {document.original_name}")

        # Validate page ranges
        import fitz
        source_doc = fitz.open(str(pdf_path))
        total_pages = len(source_doc)
        source_doc.close()

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
            split_name = split.get("name", "").strip()

            # Generate name if not provided
            if not split_name:
                split_name = f"{document.original_name.replace('.pdf', '')}_part_{i+1}"

            print(f"  Creating split {i+1}: {split_name} (pages {start_page+1}-{end_page+1})")

            # Create new document for this split
            split_doc = fitz.open()
            split_doc.insert_pdf(source_doc, from_page=start_page, to_page=end_page)

            # Save split document
            output_filename = f"{uuid.uuid4()}_{split_name}.pdf"
            output_path = DOCS_DIR / output_filename
            split_doc.save(str(output_path))
            split_doc.close()

            # Calculate file hash and size
            file_size = output_path.stat().st_size
            with open(output_path, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()

            # Create new document record in database
            try:
                new_document = db.create_document(
                    filename=output_filename,
                    original_name=f"{split_name}.pdf",
                    file_size=file_size,
                    file_path=str(output_path),
                    client_id=document.client_id,
                    persona=document.persona or "System",
                    job_role=document.job_role or "PDF Split",
                    file_hash=file_hash
                )

                created_documents.append({
                    "id": new_document.id,
                    "name": f"{split_name}.pdf",
                    "filename": output_filename,
                    "size": file_size,
                    "pages": end_page - start_page + 1,
                    "page_range": f"{start_page+1}-{end_page+1}"
                })

            except Exception as db_error:
                # Clean up file if database insert failed
                output_path.unlink(missing_ok=True)
                raise HTTPException(status_code=500, detail=f"Failed to save split document to database: {str(db_error)}")

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
async def merge_documents(request: Request):
    """Merge multiple PDF documents into a single PDF"""
    try:
        body = await request.json()
        document_ids = body.get("document_ids", [])
        output_name = body.get("output_name", "").strip()

        if len(document_ids) < 2:
            raise HTTPException(status_code=400, detail="At least 2 documents required for merging")

        print(f"🔗 Merging {len(document_ids)} documents")
        print(f"📝 Output name: '{output_name}' (empty will auto-generate)")

        # Get documents from database
        documents = []
        for doc_id in document_ids:
            doc = db.get_document_by_id(doc_id)
            if not doc:
                raise HTTPException(status_code=404, detail=f"Document {doc_id} not found")
            documents.append(doc)

        # Verify all files exist
        pdf_paths = []
        for doc in documents:
            pdf_path = Path(doc.file_path)
            if not pdf_path.exists():
                raise HTTPException(status_code=404, detail=f"PDF file not found: {doc.original_name}")
            pdf_paths.append(pdf_path)

        # Generate output filename
        if not output_name:
            # Auto-generate name: merged_pdf_1, merged_pdf_2, etc.
            counter = 1
            while True:
                auto_name = f"merged_pdf_{counter}"
                # Check if this name already exists in database
                existing = db.search_documents(auto_name)
                if not any(doc.original_name.startswith(auto_name) for doc in existing):
                    output_name = auto_name
                    break
                counter += 1

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
        output_filename = f"{uuid.uuid4()}_{output_name}.pdf"
        output_path = DOCS_DIR / output_filename
        merged_doc.save(str(output_path))
        merged_doc.close()

        # Calculate file hash and size
        file_size = output_path.stat().st_size
        with open(output_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()

        # Create new document record in database
        try:
            new_document = db.create_document(
                filename=output_filename,
                original_name=f"{output_name}.pdf",
                file_size=file_size,
                file_path=str(output_path),
                client_id=None,
                persona="System",
                job_role="PDF Merge",
                file_hash=file_hash
            )
            new_doc_id = new_document.id
        except Exception as db_error:
            # Clean up file if database insert failed
            output_path.unlink(missing_ok=True)
            raise HTTPException(status_code=500, detail=f"Failed to save merged document to database: {str(db_error)}")

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
async def get_library_statistics(current_user: dict = Depends(get_optional_user)):
    """
    Get library statistics for chatbot context
    Returns document counts, types, and recent activity
    """
    try:
        user_id = current_user.get("sub") if current_user else "anonymous"
        
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
    current_page: Optional[int] = None  # NEW: Current page number in PDF viewer
    context_type: str = "library"  # NEW: "library" or "pdf_viewer"
    conversation_history: Optional[List[Dict[str, str]]] = []
    session_id: Optional[str] = None  # NEW: Chat session ID for history tracking

@app.post("/api/chat")
async def chat_endpoint(
    request: ChatRequest,
    current_user: dict = Depends(get_optional_user)
):
    """
    Handle chat messages with AI assistant using context-aware RAG
    Supports library and PDF viewer contexts with semantic search
    """
    try:
        if not llm_provider:
            raise HTTPException(status_code=503, detail="LLM service not available")

        # Get user ID (optional for unauthenticated access)
        user_id = current_user.get("sub") if current_user else "00000000-0000-0000-0000-000000000000"
        
        # DEBUG LOGGING
        with open("backend_debug.log", "a", encoding="utf-8") as f:
            f.write(f"\n--- Request at {datetime.now().isoformat()} ---\n")
            f.write(f"User ID: {user_id}\n")
            f.write(f"Message: {request.message}\n")
            f.write(f"Context Type: {request.context_type}\n")

        print(f"👤 User ID: {user_id}")
        
        # Import context builder and RAG service  
        from .context_builder import build_library_context, build_pdf_context, build_enriched_messages, search_library_documents
        from .rag_service import get_rag_service
        from .chat_history import get_chat_history_manager
        
        # Initialize chat history manager
        chat_mgr = get_chat_history_manager()
        
        # Create or get session
        session_id = request.session_id
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
                    document_id=None,  # Search all documents
                    user_id=user_id,
                    llm_provider=None,
                    use_advanced_rag=False
                )

                # Filter out results from current document and format
                doc_name_cache = {}
                try:
                    all_docs = db.get_all_documents(user_id)
                    for doc in all_docs:
                        doc_name_cache[doc.id] = doc.original_name or doc.filename or f"Document"
                except:
                    pass

                for result in cross_results:
                    if result.document_id != request.document_id:
                        cross_doc_suggestions.append({
                            'document_id': result.document_id,
                            'document_name': doc_name_cache.get(result.document_id, 'Document'),
                            'page_number': result.page_number or 1,
                            'text': result.chunk_text[:150] + '...' if len(result.chunk_text) > 150 else result.chunk_text,
                            'similarity': round(result.similarity_score, 3) if result.similarity_score else 0.5
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
            
            # DEBUG LOGGING
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
    
    except Exception as e:
        print(f"❌ Chat endpoint error: {e}")
        import traceback
        traceback.print_exc()
        
        # Log to file for debugging
        with open("backend_error.log", "a", encoding="utf-8") as f:
            f.write(f"\n\n--- Error at {datetime.now().isoformat()} ---\n")
            f.write(f"Error: {str(e)}\n")
            f.write(traceback.format_exc())
        
        # Fallback response
        # Fallback response with specific error if safe
        error_msg = str(e)
        user_msg = "I apologize, but I encountered an error processing your request."
        
        # Check for known safe error messages to show to user
        safe_errors = ["quota", "429", "resourceexhausted", "invalidargument", "context window", "api key"]
        if any(err in error_msg.lower() for err in safe_errors):
             user_msg = f"Service Error: {error_msg}"
        
        return {
            "response": user_msg,
            "error": error_msg,
            "success": False,
            "timestamp": datetime.now().isoformat()
        }


# RAG endpoints
@app.post("/api/rag/process/{document_id}")
async def process_document_for_rag(document_id: str):
    """
    Process a single document for RAG
    Chunks, embeds, and stores in vector database
    """
    try:
        from .rag_service import get_rag_service
        rag_service = get_rag_service()
        
        # Get all documents
        documents = db.get_all_documents()
        
        if not documents:
            return {
                "success": True,
                "message": "No documents to process",
                "processed": 0
            }
        
        # Process each document
        results = []
        for document in documents:
            # Check if already processed
            existing_chunks = db.get_chunk_count(document.id)
            if existing_chunks > 0:
                print(f"⏭️ Skipping {document.original_name} (already processed)")
                continue
            
            # Check if file exists
            file_path = Path(document.file_path)
            if not file_path.exists():
                print(f"❌ File not found: {document.original_name}")
                continue
            
            # Process
            result = await rag_service.process_document(
                document_id=document.id,
                pdf_path=str(file_path),
                batch_size=32
            )
            results.append(result)
        
        successful = sum(1 for r in results if r.get('success', False))
        
        return {
            "success": True,
            "total_documents": len(documents),
            "processed": len(results),
            "successful": successful,
            "results": results
        }
        
    except Exception as e:
        print(f"❌ Error processing all documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/rag/document/{document_id}")
async def delete_document_from_rag(document_id: str):
    """Remove document from RAG system"""
    try:
        from .rag_service import get_rag_service
        rag_service = get_rag_service()
        
        result = rag_service.delete_document_from_rag(document_id)
        return result
        
    except Exception as e:
        print(f"❌ Error deleting document from RAG: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Catch-all route for SPA routing (MUST be last)
@app.get("/{path:path}")
async def serve_frontend(path: str):
    """Serve React app for all routes (SPA routing)"""
    # Serve static files with proper MIME types
    static_file = Path("../frontend/dist") / path
    if static_file.exists() and static_file.is_file():
        # Determine MIME type based on file extension
        if path.endswith('.js'):
            media_type = "application/javascript"
        elif path.endswith('.css'):
            media_type = "text/css"
        elif path.endswith('.html'):
            media_type = "text/html"
        elif path.endswith('.json'):
            media_type = "application/json"
        else:
            media_type = None

        return FileResponse(static_file, media_type=media_type)

    # For all other routes, serve the React app (SPA routing)
    return await get_frontend()


print("✅✅✅ APPLICATION MODULE LOADED SUCCESSFULLY ✅✅✅")
print("🎉 Ready to accept connections!")
sys.stdout.flush()
