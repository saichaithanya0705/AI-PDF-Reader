"""
API routes for document management
"""

from fastapi import APIRouter, HTTPException, Query, Path
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from pathlib import Path as FilePath
from datetime import datetime
import json
import shutil

from .database import db, Document
from .persona_classifier import classify_user_intent, get_persona_job_suggestions

router = APIRouter(prefix="/api", tags=["documents"])

@router.get("/documents", response_model=Dict[str, Any])
async def get_all_documents(
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Maximum number of documents to return"),
    offset: int = Query(0, ge=0, description="Number of documents to skip"),
    client_id: Optional[str] = Query(None, description="Filter by client ID"),
    search: Optional[str] = Query(None, description="Search in document names and metadata")
):
    """
    Get all documents with optional filtering and pagination
    """
    try:
        print(f"📚 API: get_all_documents called with limit={limit}, offset={offset}, client_id={client_id}, search={search}")

        if search:
            documents = db.search_documents(search)
            print(f"📚 API: Found {len(documents)} documents matching search '{search}'")
        elif client_id:
            documents = db.get_documents_by_client(client_id)
            print(f"📚 API: Found {len(documents)} documents for client '{client_id}'")
        else:
            documents = db.get_all_documents(limit=limit, offset=offset)
            print(f"📚 API: Found {len(documents)} total documents")

        # Convert documents to dictionaries for JSON response
        document_dicts = []
        for doc in documents:
            doc_dict = doc.to_dict()
            # Add file URL for frontend
            doc_dict['url'] = f"/api/files/{doc.filename}"
            document_dicts.append(doc_dict)
            print(f"📄 API: Document {doc.id}: {doc.original_name} ({doc.filename})")

        stats = db.get_document_stats()
        print(f"📊 API: Database stats: {stats}")

        response_data = {
            "documents": document_dicts,
            "count": len(document_dicts),
            "total_count": stats['total_documents'],
            "stats": stats
        }

        print(f"📤 API: Returning {len(document_dicts)} documents to frontend")
        return response_data
        
    except Exception as e:
        print(f"❌ Error fetching documents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch documents: {str(e)}")

@router.get("/documents/{document_id}", response_model=Dict[str, Any])
async def get_document(
    document_id: str = Path(..., description="Document ID")
):
    """
    Get a specific document by ID
    """
    try:
        document = db.get_document_by_id(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        doc_dict = document.to_dict()
        doc_dict['url'] = f"/api/files/{document.filename}"
        
        # Update last opened time
        db.update_last_opened(document_id)
        
        return {
            "document": doc_dict,
            "success": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error fetching document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch document: {str(e)}")

@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str = Path(..., description="Document ID"),
    permanent: bool = Query(False, description="Permanently delete (default: soft delete)")
):
    """
    Delete a document (soft delete by default)
    """
    try:
        # Get document info before deleting
        document = db.get_document_by_id(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Delete from database
        success = db.delete_document(document_id, soft_delete=not permanent)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete document from database")
        
        # Delete physical file if permanent deletion
        if permanent:
            file_path = FilePath(document.file_path)
            if file_path.exists():
                file_path.unlink()
                print(f"🗑️ Deleted file: {document.filename}")
        
        print(f"🗑️ {'Permanently deleted' if permanent else 'Soft deleted'} document: {document_id}")
        
        return {
            "success": True,
            "message": f"Document {'permanently deleted' if permanent else 'deleted'} successfully",
            "document_id": document_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error deleting document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

@router.put("/documents/{document_id}")
async def update_document(
    document_id: str = Path(..., description="Document ID"),
    updates: Dict[str, Any] = None
):
    """
    Update document metadata
    """
    try:
        if not updates:
            raise HTTPException(status_code=400, detail="No updates provided")
        
        # Check if document exists
        document = db.get_document_by_id(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Filter allowed updates (security)
        allowed_fields = {
            'original_name', 'persona', 'job_role', 'status', 'processing_status',
            'validation_result', 'metadata', 'tags'
        }
        
        filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
        
        if not filtered_updates:
            raise HTTPException(status_code=400, detail="No valid updates provided")
        
        success = db.update_document(document_id, **filtered_updates)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update document")
        
        # Return updated document
        updated_document = db.get_document_by_id(document_id)
        doc_dict = updated_document.to_dict()
        doc_dict['url'] = f"/api/files/{updated_document.filename}"
        
        return {
            "success": True,
            "message": "Document updated successfully",
            "document": doc_dict
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error updating document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update document: {str(e)}")

@router.get("/documents/search/{query}")
async def search_documents(
    query: str = Path(..., description="Search query"),
    fields: Optional[List[str]] = Query(None, description="Fields to search in")
):
    """
    Search documents by text query
    """
    try:
        documents = db.search_documents(query, fields)
        
        document_dicts = []
        for doc in documents:
            doc_dict = doc.to_dict()
            doc_dict['url'] = f"/api/files/{doc.filename}"
            document_dicts.append(doc_dict)
        
        return {
            "documents": document_dicts,
            "count": len(document_dicts),
            "query": query,
            "fields_searched": fields or ['original_name', 'filename', 'persona', 'job_role']
        }
        
    except Exception as e:
        print(f"❌ Error searching documents: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/documents/stats")
async def get_document_stats():
    """
    Get document database statistics
    """
    try:
        stats = db.get_document_stats()
        return {
            "success": True,
            "stats": stats
        }
        
    except Exception as e:
        print(f"❌ Error getting document stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@router.post("/documents/{document_id}/validate")
async def validate_document(
    document_id: str = Path(..., description="Document ID"),
    validation_result: Dict[str, Any] = None
):
    """
    Store validation result for a document
    """
    try:
        document = db.get_document_by_id(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        success = db.update_document(document_id, validation_result=validation_result)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to store validation result")
        
        return {
            "success": True,
            "message": "Validation result stored successfully",
            "document_id": document_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error storing validation for document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to store validation: {str(e)}")

@router.post("/documents/{document_id}/process")
async def update_processing_status(
    document_id: str = Path(..., description="Document ID"),
    status: str = Query(..., description="Processing status"),
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Update document processing status and metadata
    """
    try:
        document = db.get_document_by_id(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        updates = {"processing_status": status}
        if metadata:
            updates["metadata"] = metadata
        
        success = db.update_document(document_id, **updates)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update processing status")
        
        return {
            "success": True,
            "message": f"Processing status updated to: {status}",
            "document_id": document_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error updating processing status for document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update processing status: {str(e)}")

@router.post("/documents/{document_id}/open")
async def mark_document_opened(
    document_id: str = Path(..., description="Document ID")
):
    """
    Mark a document as opened (update last_opened timestamp)
    """
    try:
        document = db.get_document_by_id(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        success = db.update_last_opened(document_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update open time")

        return {
            "success": True,
            "message": "Document marked as opened",
            "document_id": document_id,
            "opened_at": datetime.now().isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error marking document as opened {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to mark document as opened: {str(e)}")

@router.get("/documents/sorted/{sort_by}")
async def get_documents_sorted(
    sort_by: str = Path(..., description="Sort field: upload_date, last_uploaded, last_opened, name, size"),
    sort_order: str = Query("desc", description="Sort order: asc or desc"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Maximum number of documents")
):
    """
    Get documents sorted by specified field
    """
    try:
        documents = db.get_documents_sorted(sort_by=sort_by, sort_order=sort_order, limit=limit)

        # Convert documents to dictionaries for JSON response
        document_dicts = []
        for doc in documents:
            doc_dict = doc.to_dict()
            # Add file URL for frontend
            doc_dict['url'] = f"/api/files/{doc.filename}"
            document_dicts.append(doc_dict)

        return {
            "documents": document_dicts,
            "count": len(document_dicts),
            "sort_by": sort_by,
            "sort_order": sort_order,
            "success": True
        }

    except Exception as e:
        print(f"❌ Error getting sorted documents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get sorted documents: {str(e)}")

@router.delete("/documents")
async def delete_all_documents(
    permanent: bool = Query(False, description="Permanently delete all documents (default: soft delete)"),
    client_id: Optional[str] = Query(None, description="Delete only documents for specific client")
):
    """
    Delete all documents (soft delete by default)
    """
    try:
        # Get all documents first (for cleanup if permanent delete)
        if client_id:
            documents = db.get_documents_by_client(client_id)
            target_description = f"all documents for client {client_id}"
        else:
            documents = db.get_all_documents()
            target_description = "all documents"
        
        if not documents:
            return {
                "success": True,
                "message": f"No documents found to delete",
                "deleted_count": 0
            }
        
        deleted_count = 0
        failed_deletes = []
        
        for document in documents:
            try:
                # Delete from database
                success = db.delete_document(document.id, soft_delete=not permanent)
                if success:
                    deleted_count += 1
                    
                    # Delete physical file if permanent deletion
                    if permanent:
                        file_path = FilePath(document.file_path)
                        if file_path.exists():
                            file_path.unlink()
                            print(f"🗑️ Deleted file: {document.filename}")
                else:
                    failed_deletes.append(document.id)
                    
            except Exception as e:
                print(f"❌ Error deleting document {document.id}: {e}")
                failed_deletes.append(document.id)
        
        # Clean up empty directories if permanent delete
        if permanent and deleted_count > 0:
            try:
                docs_dir = FilePath("data/docs")
                if docs_dir.exists() and not any(docs_dir.iterdir()):
                    print("📁 Cleaned up empty docs directory")
            except Exception as e:
                print(f"⚠️ Failed to clean up directories: {e}")
        
        success_message = f"{'Permanently deleted' if permanent else 'Soft deleted'} {deleted_count} documents"
        if failed_deletes:
            success_message += f" ({len(failed_deletes)} failed)"
        
        print(f"🗑️ {success_message}")
        
        return {
            "success": True,
            "message": success_message,
            "deleted_count": deleted_count,
            "failed_count": len(failed_deletes),
            "failed_document_ids": failed_deletes,
            "permanent": permanent
        }
        
    except Exception as e:
        print(f"❌ Error deleting {target_description}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete documents: {str(e)}")

@router.put("/documents/{document_id}/rename")
async def rename_document(
    document_id: str = Path(..., description="Document ID"),
    new_name: str = Query(..., description="New document name")
):
    """
    Rename a document (update original_name)
    """
    try:
        # Validate input
        if not new_name or not new_name.strip():
            raise HTTPException(status_code=400, detail="New name cannot be empty")
        
        new_name = new_name.strip()
        
        # Check if document exists
        document = db.get_document_by_id(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        old_name = document.original_name
        
        # Check if name is actually different
        if new_name == old_name:
            return {
                "success": True,
                "message": "Document name unchanged",
                "document_id": document_id,
                "old_name": old_name,
                "new_name": new_name
            }
        
        # Update the document name
        success = db.update_document(document_id, original_name=new_name)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update document name in database")
        
        print(f"✏️ Renamed document {document_id}: '{old_name}' → '{new_name}'")
        
        # Return updated document
        updated_document = db.get_document_by_id(document_id)
        doc_dict = updated_document.to_dict()
        doc_dict['url'] = f"/api/files/{updated_document.filename}"
        
        return {
            "success": True,
            "message": f"Document renamed successfully",
            "document_id": document_id,
            "old_name": old_name,
            "new_name": new_name,
            "document": doc_dict
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error renaming document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to rename document: {str(e)}")

@router.delete("/documents/{document_id}/force")
async def force_delete_document(
    document_id: str = Path(..., description="Document ID"),
    remove_file: bool = Query(True, description="Also remove physical file")
):
    """
    Force delete a document (permanent deletion with file removal)
    """
    try:
        # Get document info before deleting
        document = db.get_document_by_id(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Delete physical file first if requested
        file_deleted = False
        if remove_file:
            file_path = FilePath(document.file_path)
            if file_path.exists():
                file_path.unlink()
                file_deleted = True
                print(f"🗑️ Deleted file: {document.filename}")
        
        # Delete from database (permanent)
        success = db.delete_document(document_id, soft_delete=False)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete document from database")
        
        print(f"🗑️ Force deleted document: {document_id} ({document.original_name})")
        
        return {
            "success": True,
            "message": f"Document permanently deleted",
            "document_id": document_id,
            "document_name": document.original_name,
            "file_deleted": file_deleted,
            "file_path": document.file_path if remove_file else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error force deleting document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to force delete document: {str(e)}")

@router.post("/documents/bulk-delete")
async def bulk_delete_documents(
    document_ids: List[str],
    permanent: bool = Query(False, description="Permanently delete documents (default: soft delete)")
):
    """
    Delete multiple documents in bulk
    """
    try:
        if not document_ids:
            raise HTTPException(status_code=400, detail="No document IDs provided")
        
        deleted_count = 0
        failed_deletes = []
        deleted_files = []
        
        for doc_id in document_ids:
            try:
                # Get document info before deleting
                document = db.get_document_by_id(doc_id)
                if not document:
                    failed_deletes.append({"id": doc_id, "reason": "Document not found"})
                    continue
                
                # Delete from database
                success = db.delete_document(doc_id, soft_delete=not permanent)
                if success:
                    deleted_count += 1
                    
                    # Delete physical file if permanent deletion
                    if permanent:
                        file_path = FilePath(document.file_path)
                        if file_path.exists():
                            file_path.unlink()
                            deleted_files.append(document.filename)
                            print(f"🗑️ Deleted file: {document.filename}")
                else:
                    failed_deletes.append({"id": doc_id, "reason": "Database deletion failed"})
                    
            except Exception as e:
                print(f"❌ Error deleting document {doc_id}: {e}")
                failed_deletes.append({"id": doc_id, "reason": str(e)})
        
        success_message = f"{'Permanently deleted' if permanent else 'Soft deleted'} {deleted_count}/{len(document_ids)} documents"
        
        print(f"🗑️ Bulk delete: {success_message}")
        
        return {
            "success": True,
            "message": success_message,
            "requested_count": len(document_ids),
            "deleted_count": deleted_count,
            "failed_count": len(failed_deletes),
            "failed_deletes": failed_deletes,
            "deleted_files": deleted_files if permanent else [],
            "permanent": permanent
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error bulk deleting documents: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to bulk delete documents: {str(e)}")


# Pydantic models for AI persona/job classification
class UserIntentRequest(BaseModel):
    user_input: str
    include_suggestions: bool = True


class PersonaJobSuggestionsRequest(BaseModel):
    user_input: str
    top_k: int = 3


# AI-powered persona and job classification endpoints
@router.post("/classify-intent", response_model=Dict[str, Any])
async def classify_user_intent_endpoint(request: UserIntentRequest):
    """
    Classify user intent into appropriate persona and job using AI/NLP
    
    This endpoint uses sentence transformers and similarity matching to:
    1. Understand user's natural language input
    2. Match to the best fitting persona from available options
    3. Suggest the most relevant job/task
    4. Provide confidence scores and reasoning
    """
    try:
        print(f"🤖 Classifying user intent: '{request.user_input}'")
        
        # Use the AI classifier
        result = classify_user_intent(request.user_input)
        
        # Optionally include alternative suggestions
        if request.include_suggestions and result['combined_confidence'] < 0.8:
            suggestions = get_persona_job_suggestions(request.user_input, top_k=3)
            result['alternatives'] = suggestions
        
        print(f"✅ Classification result: Persona='{result['persona']['name']}' ({result['persona']['confidence']:.2f}), Job='{result['job']['name']}' ({result['job']['confidence']:.2f})")
        
        return {
            "status": "success",
            "classification": result,
            "message": "Intent classified successfully"
        }
        
    except Exception as e:
        print(f"❌ Error classifying user intent: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to classify intent: {str(e)}")


@router.post("/persona-job-suggestions", response_model=Dict[str, Any])
async def get_persona_job_suggestions_endpoint(request: PersonaJobSuggestionsRequest):
    """
    Get alternative persona and job suggestions based on user input
    
    Returns top-k most similar personas and jobs with confidence scores
    """
    try:
        print(f"🔍 Getting suggestions for: '{request.user_input}' (top {request.top_k})")
        
        suggestions = get_persona_job_suggestions(request.user_input, request.top_k)
        
        print(f"✅ Found {len(suggestions.get('personas', []))} persona and {len(suggestions.get('jobs', []))} job suggestions")
        
        return {
            "status": "success",
            "suggestions": suggestions,
            "message": "Suggestions retrieved successfully"
        }
        
    except Exception as e:
        print(f"❌ Error getting suggestions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get suggestions: {str(e)}")


@router.get("/available-personas", response_model=Dict[str, Any])
async def get_available_personas():
    """
    Get all available personas with their descriptions
    """
    try:
        from .persona_classifier import classifier
        
        personas = {}
        for name, info in classifier.personas.items():
            personas[name] = {
                'description': info['description'],
                'domains': info['related_domains'],
                'keywords': info['keywords'][:5]  # Only first 5 keywords
            }
        
        return {
            "status": "success",
            "personas": personas,
            "count": len(personas),
            "message": "Available personas retrieved successfully"
        }
        
    except Exception as e:
        print(f"❌ Error getting available personas: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get personas: {str(e)}")


@router.get("/available-jobs", response_model=Dict[str, Any])
async def get_available_jobs():
    """
    Get all available jobs with their descriptions
    """
    try:
        from .persona_classifier import classifier
        
        jobs = {}
        for name, info in classifier.jobs.items():
            jobs[name] = {
                'description': info['description'],
                'domains': info['related_domains'],
                'keywords': info['keywords'][:5]  # Only first 5 keywords
            }
        
        return {
            "status": "success",
            "jobs": jobs,
            "count": len(jobs),
            "message": "Available jobs retrieved successfully"
        }
        
    except Exception as e:
        print(f"❌ Error getting available jobs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get jobs: {str(e)}")
