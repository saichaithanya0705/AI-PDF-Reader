"""
Script to process existing PDF documents for RAG
Chunks, embeds, and stores all documents in the database
"""
import argparse
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
import os

load_dotenv()

# Determine which database to use
USE_SUPABASE = os.getenv("USE_SUPABASE", "false").lower() == "true"
if USE_SUPABASE:
    print("🚀 Using Supabase Database")
    from app.supabase_database import get_supabase_db
    db = get_supabase_db()
else:
    print("📂 Using Local SQLite Database")
    from app.database import db

from app.rag_service import get_rag_service


def _get_documents_for_scope(client_id=None, all_tenants=False):
    if bool(client_id) == bool(all_tenants):
        raise ValueError("Specify exactly one tenant scope: client_id or all_tenants=True")

    if client_id:
        return db.get_all_documents(client_id=client_id)

    return db.get_all_documents()


async def process_all_documents(client_id=None, all_tenants=False, batch_size=32, force=True):
    """Process all documents in the database for RAG"""
    print("=" * 60)
    print("📚 Processing Existing Documents for RAG")
    if client_id:
        print(f"🔒 Tenant scope: {client_id}")
    elif all_tenants:
        print("🌐 Tenant scope: all tenants")
    print("=" * 60)
    
    # Get RAG service
    rag_service = get_rag_service()
    
    # Get all documents
    documents = _get_documents_for_scope(client_id=client_id, all_tenants=all_tenants)
    
    if not documents:
        print("⚠️ No documents found in database")
        return
    
    print(f"\n📄 Found {len(documents)} documents to process\n")
    
    # Process each document
    results = []
    for i, document in enumerate(documents, 1):
        print(f"\n[{i}/{len(documents)}] Processing: {document.original_name}")
        print(f"  Document ID: {document.id}")
        print(f"  File path: {document.file_path}")
        print(f"  Tenant: {getattr(document, 'client_id', None) or 'missing'}")

        document_client_id = getattr(document, 'client_id', None)
        if not document_client_id:
            print("  ❌ Document has no client_id; refusing tenant-unsafe RAG backfill")
            results.append({
                'document_id': document.id,
                'success': False,
                'error': 'Document missing client_id'
            })
            continue
        
        # Check if file exists
        file_path = Path(document.file_path)
        if not file_path.exists():
            print(f"  ❌ File not found: {file_path}")
            results.append({
                'document_id': document.id,
                'success': False,
                'error': 'File not found'
            })
            continue
        
        # Check if already processed
        existing_chunks = db.get_chunk_count(document.id)
        if existing_chunks > 0:
            if force:
                print(f"  ℹ️ Document already has {existing_chunks} chunks. Force re-processing...")
            else:
                print(f"  ⏭️ Document already has {existing_chunks} chunks. Skipping.")
                results.append({
                    'document_id': document.id,
                    'success': True,
                    'chunks_created': existing_chunks,
                    'skipped': True
                })
                continue
        
        # Process document
        result = await rag_service.process_document(
            document_id=document.id,
            pdf_path=str(file_path),
            user_id=document_client_id,
            batch_size=batch_size
        )
        
        results.append(result)
        
        if result['success']:
            print(f"  ✅ Processed successfully:")
            print(f"     - Chunks: {result.get('chunks_created', 0)}")
            print(f"     - Embeddings: {result.get('embeddings_generated', 0)}")
            print(f"     - Time: {result.get('elapsed_seconds', 0)}s")
        else:
            print(f"  ❌ Failed: {result.get('error', 'Unknown error')}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 Processing Summary")
    print("=" * 60)
    
    successful = sum(1 for r in results if r.get('success', False))
    failed = len(results) - successful
    skipped = sum(1 for r in results if r.get('skipped', False))
    total_chunks = sum(r.get('chunks_created', 0) for r in results)
    
    print(f"\nDocuments processed: {len(results)}")
    print(f"  ✅ Successful: {successful}")
    print(f"  ⏭️ Skipped: {skipped}")
    print(f"  ❌ Failed: {failed}")
    print(f"\nTotal chunks created: {total_chunks}")
    
    # Show RAG stats
    print("\n" + "-" * 60)
    print("RAG System Statistics")
    print("-" * 60)
    stats = rag_service.get_stats()
    print(f"\nVector Store:")
    print(f"  Total vectors: {stats['vector_store']['total_vectors']}")
    print(f"  Documents: {stats['vector_store']['num_documents']}")
    print(f"\nDatabase:")
    print(f"  Total chunks: {stats['database']['total_chunks']}")
    print(f"\nEmbedding Model:")
    print(f"  Model: {stats['embedding']['model']}")
    print(f"  Dimension: {stats['embedding']['dimension']}")
    
    print("\n✅ Processing complete!")


def _parse_args():
    parser = argparse.ArgumentParser(description="Backfill existing PDF documents into RAG indexes")
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--client-id", help="Backfill only documents owned by this tenant/client")
    scope.add_argument("--all-tenants", action="store_true", help="Backfill documents for every tenant")
    parser.add_argument("--batch-size", type=int, default=32, help="Embedding batch size")
    parser.add_argument("--skip-existing", action="store_true", help="Skip documents that already have chunks")
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    print("Starting document processing...\n")
    asyncio.run(process_all_documents(
        client_id=args.client_id,
        all_tenants=args.all_tenants,
        batch_size=args.batch_size,
        force=not args.skip_existing,
    ))
