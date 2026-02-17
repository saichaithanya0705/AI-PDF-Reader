"""
Script to process existing PDF documents for RAG
Chunks, embeds, and stores all documents in the database
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import db
from app.rag_service import get_rag_service


async def process_all_documents():
    """Process all documents in the database for RAG"""
    print("=" * 60)
    print("📚 Processing Existing Documents for RAG")
    print("=" * 60)
    
    # Get RAG service
    rag_service = get_rag_service()
    
    # Get all documents
    documents = db.get_all_documents()
    
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
            print(f"  ℹ️ Document already has {existing_chunks} chunks. Skipping...")
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
            batch_size=32
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


if __name__ == "__main__":
    print("Starting document processing...\n")
    asyncio.run(process_all_documents())
