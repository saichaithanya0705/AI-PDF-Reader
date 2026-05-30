"""
Context Builder Module for Context-Aware Chatbot

This module builds contextual information for the chatbot based on the current view:
- Library page: Document statistics and management context
- PDF viewer: Current page content, metadata, and cross-document search
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
import os

logger = logging.getLogger(__name__)


async def build_library_context(db, user_id: str) -> Dict[str, Any]:
    """
    Build context for library page chatbot interactions
    
    Args:
        db: Database instance
        user_id: User identifier
        
    Returns:
        Dictionary containing library statistics and context
    """
    try:
        debug_logging = os.getenv("DEBUG_CHAT_LOGGING", "false").lower() == "true"
        if debug_logging:
            with open("backend_debug.log", "a", encoding="utf-8") as f:
                f.write(f"Building library context for user_id: {user_id}\n")

        # Get all documents for this authenticated user from SQLite.
        documents = db.get_all_documents(client_id=user_id)
        
        if debug_logging:
            with open("backend_debug.log", "a", encoding="utf-8") as f:
                f.write(f"Retrieved {len(documents)} documents\n")
        
        # Calculate statistics
        total_docs = len(documents)
        
        # Count by status
        status_counts = {}
        for doc in documents:
            status = doc.status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Get recent uploads (last 7 days)
        # Ensure we compare compatible datetimes
        now = datetime.now()
        seven_days_ago = now - timedelta(days=7)
        
        recent_docs = []
        for doc in documents:
            if not doc.upload_date:
                continue
                
            # Handle timezone awareness
            doc_date = doc.upload_date
            if doc_date.tzinfo is not None and seven_days_ago.tzinfo is None:
                # Make doc_date naive (remove timezone) or make seven_days_ago aware
                # Easiest is to remove timezone from doc_date for comparison
                doc_date = doc_date.replace(tzinfo=None)
            elif doc_date.tzinfo is None and seven_days_ago.tzinfo is not None:
                seven_days_ago = seven_days_ago.replace(tzinfo=None)
                
            if doc_date > seven_days_ago:
                recent_docs.append(doc)
        
        # Calculate total size (in MB)
        total_size = sum(doc.file_size for doc in documents)
        total_size_mb = total_size / (1024 * 1024)
        
        # Get document types (by extension)
        doc_types = {}
        for doc in documents:
            filename = doc.filename or doc.original_name
            ext = filename.split('.')[-1].lower() if '.' in filename else 'unknown'
            doc_types[ext] = doc_types.get(ext, 0) + 1
        
        # Recent uploads (top 5)
        sorted_docs = sorted(
            documents,
            key=lambda d: d.upload_date or datetime.min,
            reverse=True
        )
        recent_uploads = [
            {
                'name': doc.original_name or doc.filename or 'Unknown',
                'id': doc.id,
                'upload_date': doc.upload_date.isoformat() if doc.upload_date else None
            }
            for doc in sorted_docs[:5]
        ]
        
        # Get all document summaries (limit to 20 for context efficiency)
        doc_summaries = []
        for doc in sorted_docs[:20]:
            doc_summaries.append({
                'name': doc.original_name or doc.filename or 'Unknown',
                'id': doc.id,
                'pages': 'unknown', # page_count not in Document model
                'upload_date': doc.upload_date.isoformat() if doc.upload_date else None
            })
        
        # Build document names list for system instruction
        doc_names = [d['name'] for d in doc_summaries[:10]]
        doc_list_str = ", ".join(doc_names) if doc_names else "none"
        
        # Build enhanced system instruction
        system_instruction = (
            f"You are an AI assistant helping a user manage their PDF library. "
            f"The library currently contains {total_docs} document{'s' if total_docs != 1 else ''}. "
            f"Recent activity: {len(recent_docs)} document{'s' if len(recent_docs) != 1 else ''} uploaded in the last 7 days. "
            f"Total storage: {total_size_mb:.2f} MB. "
        )
        
        if doc_names:
            system_instruction += (
                f"\n\nAvailable documents include: {doc_list_str}" +
                (f", and {len(documents) - len(doc_names)} more." if len(documents) > len(doc_names) else ".")
            )
            
        # NEW: Add rich metadata for top documents
        if documents:
            system_instruction += "\n\nDocument Insights:"
            for doc in sorted_docs[:10]:  # Limit to top 10 to avoid context overflow
                meta = doc.metadata or {}
                summary = meta.get('summary', 'No summary available.')
                topics = ", ".join(meta.get('topics', []))
                doc_type = meta.get('document_type', 'Document')
                
                system_instruction += f"\n- {doc.original_name} ({doc_type}): {summary}"
                if topics:
                    system_instruction += f" [Topics: {topics}]"
        
        system_instruction += (
            "\n\nYou can answer questions about the library contents, specific documents, statistics, "
            "and help with document management. You have access to search across all documents."
        )
        
        return {
            "type": "library",
            "statistics": {
                "total_documents": total_docs,
                "status_counts": status_counts,
                "document_types": doc_types,
                "total_size_mb": round(total_size_mb, 2),
                "recent_uploads_count": len(recent_docs)
            },
            "recent_uploads": recent_uploads,
            "document_summaries": doc_summaries,  # NEW: Full document list for chatbot awareness
            "system_instruction": system_instruction,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error building library context: {e}")
        import traceback
        traceback.print_exc()
        return {
            "type": "library",
            "statistics": {
                "total_documents": 0,
                "error": str(e)
            },
            "system_instruction": "You are an AI assistant for PDF library management.",
            "timestamp": datetime.now().isoformat()
        }


async def build_pdf_context(
    db,
    user_id: str,
    document_id: str,
    current_page: Optional[int] = None
) -> Dict[str, Any]:
    """
    Build context for PDF viewer page chatbot interactions
    
    Args:
        db: Database instance
        user_id: User identifier
        document_id: Current document ID
        current_page: Current page number (optional)
        
    Returns:
        Dictionary containing PDF context, page content, and related documents
    """
    try:
        # Get document metadata
        doc = db.get_document_by_id(document_id, client_id=user_id)

        if not doc:
            return {
                "type": "pdf_viewer",
                "error": "Document not found",
                "system_instruction": "You are an AI assistant for PDF viewing and analysis.",
                "timestamp": datetime.now().isoformat()
            }

        # Document is a dataclass, access attributes directly
        doc_name = doc.original_name or doc.filename or 'Unknown Document'
        
        # Get page content if page number provided
        page_content = None
        if current_page is not None:
            try:
                # Get chunk/content for this page
                page_content = await get_page_content(db, document_id, current_page)
            except Exception as e:
                logger.warning(f"Could not retrieve page content: {e}")
        
        # Search for related content in other documents
        related_docs = []
        if page_content:
            try:
                related_docs = await search_related_documents(
                    db=db,
                    query_text=page_content[:500],  # Use first 500 chars for search
                    current_doc_id=document_id,
                    user_id=user_id,
                    top_k=3
                )
            except Exception as e:
                logger.warning(f"Could not search related documents: {e}")
        
        # Build system instruction
        meta = doc.metadata or {}
        doc_summary = meta.get('summary', 'No summary available.')
        doc_topics = ", ".join(meta.get('topics', []))
        doc_entities = ", ".join(meta.get('entities', []))
        
        if current_page is not None:
            system_instruction = (
                f"You are viewing page {current_page} of '{doc_name}'. "
                f"\n\nDocument Summary: {doc_summary}"
                f"\nKey Topics: {doc_topics}"
                f"\nKey Entities: {doc_entities}"
                "\n\nAnswer questions about this PDF, help analyze the content, and suggest related documents from the library."
            )
        else:
            system_instruction = (
                f"You are viewing '{doc_name}'. "
                f"\n\nDocument Summary: {doc_summary}"
                f"\nKey Topics: {doc_topics}"
                f"\nKey Entities: {doc_entities}"
                "\n\nAnswer questions about this PDF and help analyze the content."
            )
            
        # NEW: Add context from other documents (summaries only)
        try:
            other_docs = db.get_all_documents(client_id=user_id)
            if other_docs:
                system_instruction += "\n\nContext from other documents in library:"
                count = 0
                for d in other_docs:
                    if d.id == document_id:
                        continue
                    if count >= 5: # Limit to 5 other docs to save tokens
                        break
                    
                    d_meta = d.metadata or {}
                    d_summary = d_meta.get('summary', 'No summary')
                    system_instruction += f"\n- {d.original_name}: {d_summary}"
                    count += 1
        except Exception as e:
            logger.warning(f"Failed to add other docs context: {e}")
        
        return {
            "type": "pdf_viewer",
            "current_document": {
                "id": document_id,
                "name": doc_name,
                "upload_date": doc.upload_date,
                "file_size": doc.file_size,
                "persona": doc.persona,
                "job_role": doc.job_role
            },
            "current_page": current_page,
            "page_content": page_content,
            "related_documents": related_docs,
            "system_instruction": system_instruction,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error building PDF context: {e}")
        return {
            "type": "pdf_viewer",
            "error": str(e),
            "system_instruction": "You are an AI assistant for PDF viewing and analysis.",
            "timestamp": datetime.now().isoformat()
        }


async def search_library_documents(
    query_text: str,
    user_id: str,
    top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    Search across all user's documents using vector similarity
    
    Args:
        query_text: Search query text
        user_id: User identifier to filter documents
        top_k: Number of results to return
        
    Returns:
        List of matching document chunks with metadata
    """
    try:
        if not query_text or not query_text.strip():
            return []

        from .rag_service import get_rag_service

        rag_service = get_rag_service()
        results = await rag_service.search_documents(
            query=query_text,
            top_k=top_k,
            user_id=user_id,
            use_advanced_rag=False,
        )
        search_results = [_format_search_result(result) for result in results]
            
        logger.info(f"Library search found {len(search_results)} results for user {user_id}")
        return search_results
        
    except Exception as e:
        logger.error(f"Error searching library documents: {e}")
        import traceback
        traceback.print_exc()
        return []


async def get_page_content(db, document_id: str, page_number: int) -> Optional[str]:
    """
    Retrieve text content for a specific page
    
    Args:
        db: Database instance
        document_id: Document ID
        page_number: Page number
        
    Returns:
        Page text content or None
    """
    try:
        chunks = db.get_chunks_by_document(document_id)
        page_chunks = [chunk for chunk in chunks if chunk.get('page_number') == page_number]

        if page_chunks:
            page_text = ' '.join([chunk.get('chunk_text', '') for chunk in page_chunks])
            return page_text
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting page content: {e}")
        return None


async def search_related_documents(
    db,
    query_text: str,
    current_doc_id: str,
    user_id: str,
    top_k: int = 3
) -> List[Dict[str, Any]]:
    """
    Search for related content across all user PDFs except current document
    
    Args:
        db: Database instance (unused for search now, but kept for signature compatibility)
        query_text: Text to search for
        current_doc_id: Current document ID to exclude
        user_id: User identifier
        top_k: Number of results to return
        
    Returns:
        List of related document chunks with document metadata
    """
    try:
        if not query_text or not query_text.strip():
            return []

        from .rag_service import get_rag_service

        rag_service = get_rag_service()
        results = await rag_service.search_documents(
            query=query_text,
            top_k=top_k,
            exclude_document_id=current_doc_id,
            user_id=user_id,
            use_advanced_rag=False,
        )
        related_docs = [_format_search_result(result) for result in results]
            
        logger.info(f"Found {len(related_docs)} related documents for user {user_id}")
        return related_docs
        
    except Exception as e:
        logger.error(f"Error searching related documents: {e}")
        import traceback
        traceback.print_exc()
        return []


def _format_search_result(result) -> Dict[str, Any]:
    from .rag_service import format_retrieval_result

    return format_retrieval_result(result, snippet_chars=200)


def build_enriched_messages(
    user_message: str,
    context: Dict[str, Any],
    conversation_history: List[Dict[str, str]]
) -> List[Dict[str, str]]:
    """
    Build enriched message list for LLM with context
    
    Args:
        user_message: User's message
        context: Context dictionary from build_library_context or build_pdf_context
        conversation_history: Previous conversation messages
        
    Returns:
        List of messages for LLM including system instruction
    """
    messages = []
    
    # Add system instruction
    system_instruction = context.get('system_instruction', 'You are a helpful AI assistant.')
    messages.append({
        "role": "system",
        "content": system_instruction
    })
    
    # Add conversation history
    messages.extend(conversation_history)
    
    # Add current user message with context
    if context.get('type') == 'library':
        stats = context.get('statistics', {})
        context_info = (
            f"[Library Context - {stats.get('total_documents', 0)} documents, "
            f"{stats.get('total_size_mb', 0)}MB total]\n\n{user_message}"
        )
    elif context.get('type') == 'pdf_viewer':
        doc_name = context.get('current_document', {}).get('name', 'Unknown')
        page_num = context.get('current_page')
        if page_num:
            context_info = f"[Viewing: {doc_name}, Page {page_num}]\n\n{user_message}"
        else:
            context_info = f"[Viewing: {doc_name}]\n\n{user_message}"
    else:
        context_info = user_message
    
    messages.append({
        "role": "user",
        "content": context_info
    })
    
    return messages
