"""
Database models and operations for PDF document management
"""

import sqlite3
import uuid
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, asdict
import json

@dataclass
class Document:
    """Document model representing a PDF file in the system"""
    id: str
    filename: str
    original_name: str
    upload_date: datetime
    file_size: int
    file_path: str
    status: str = 'uploaded'
    client_id: Optional[str] = None
    persona: Optional[str] = None
    job_role: Optional[str] = None
    processing_status: str = 'pending'
    validation_result: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    last_uploaded: Optional[datetime] = None  # Track when last uploaded/re-uploaded
    last_opened: Optional[datetime] = None    # Track when last opened/viewed
    last_accessed: Optional[datetime] = None  # General access (for backward compatibility)
    tags: Optional[List[str]] = None
    file_hash: Optional[str] = None           # For duplicate detection

    def to_dict(self) -> Dict[str, Any]:
        """Convert document to dictionary for JSON serialization"""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        if self.upload_date:
            data['upload_date'] = self.upload_date.isoformat()
        if self.last_uploaded:
            data['last_uploaded'] = self.last_uploaded.isoformat()
        if self.last_opened:
            data['last_opened'] = self.last_opened.isoformat()
        if self.last_accessed:
            data['last_accessed'] = self.last_accessed.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Document':
        """Create document from dictionary"""
        # Convert ISO strings back to datetime objects
        if 'upload_date' in data and isinstance(data['upload_date'], str):
            data['upload_date'] = datetime.fromisoformat(data['upload_date'])
        if 'last_uploaded' in data and isinstance(data['last_uploaded'], str):
            data['last_uploaded'] = datetime.fromisoformat(data['last_uploaded'])
        if 'last_opened' in data and isinstance(data['last_opened'], str):
            data['last_opened'] = datetime.fromisoformat(data['last_opened'])
        if 'last_accessed' in data and isinstance(data['last_accessed'], str):
            data['last_accessed'] = datetime.fromisoformat(data['last_accessed'])
        return cls(**data)

class DocumentDatabase:
    """Database operations for document management"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # Use absolute path relative to the backend directory
            backend_dir = Path(__file__).parent.parent  # Go up from app/ to backend/
            db_path = backend_dir / "data" / "documents.db"

        self.db_path = Path(db_path).resolve()  # Get absolute path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Ensure docs directory exists too
        docs_dir = self.db_path.parent / "docs"
        docs_dir.mkdir(exist_ok=True)

        print(f"📚 Database initialized at: {self.db_path}")
        print(f"📁 Docs directory at: {docs_dir}")
        self._init_database()
    
    def _init_database(self):
        """Initialize database with proper schema and handle migrations"""
        with sqlite3.connect(self.db_path) as conn:
            # First create the basic table structure
            conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    original_name TEXT NOT NULL,
                    upload_date TIMESTAMP NOT NULL,
                    file_size INTEGER NOT NULL,
                    file_path TEXT NOT NULL,
                    status TEXT DEFAULT 'uploaded',
                    client_id TEXT,
                    persona TEXT,
                    job_role TEXT,
                    processing_status TEXT DEFAULT 'pending',
                    validation_result TEXT,  -- JSON string
                    metadata TEXT,           -- JSON string
                    last_accessed TIMESTAMP, -- General access (backward compatibility)
                    tags TEXT,               -- JSON array as string
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Check existing columns
            cursor = conn.execute("PRAGMA table_info(documents)")
            existing_columns = {row[1] for row in cursor.fetchall()}

            # Add new columns if they don't exist
            new_columns = [
                ("last_uploaded", "TIMESTAMP"),
                ("last_opened", "TIMESTAMP"),
                ("file_hash", "TEXT")
            ]

            for col_name, col_type in new_columns:
                if col_name not in existing_columns:
                    try:
                        conn.execute(f"ALTER TABLE documents ADD COLUMN {col_name} {col_type}")
                        print(f"✅ Added column: {col_name}")
                    except Exception as e:
                        print(f"⚠️ Failed to add column {col_name}: {e}")

            # Create indexes for better performance (with error handling)
            indexes = [
                ("idx_upload_date", "upload_date"),
                ("idx_status", "status"),
                ("idx_client_id", "client_id")
            ]

            # Only create indexes for new columns if they exist
            cursor = conn.execute("PRAGMA table_info(documents)")
            current_columns = {row[1] for row in cursor.fetchall()}

            if "last_uploaded" in current_columns:
                indexes.append(("idx_last_uploaded", "last_uploaded"))
            if "last_opened" in current_columns:
                indexes.append(("idx_last_opened", "last_opened"))
            if "file_hash" in current_columns:
                indexes.append(("idx_file_hash", "file_hash"))

            for index_name, column_name in indexes:
                try:
                    conn.execute(f"CREATE INDEX IF NOT EXISTS {index_name} ON documents({column_name})")
                except Exception as e:
                    print(f"⚠️ Failed to create index {index_name}: {e}")

            # Update existing documents to set last_uploaded = upload_date if null
            try:
                if "last_uploaded" in current_columns:
                    conn.execute("""
                        UPDATE documents
                        SET last_uploaded = upload_date
                        WHERE last_uploaded IS NULL
                    """)
                    print("✅ Updated existing documents with last_uploaded timestamps")
            except Exception as e:
                print(f"⚠️ Failed to update existing documents: {e}")

            conn.commit()
    
            # Create document_chunks table for RAG
            conn.execute("""
                CREATE TABLE IF NOT EXISTS document_chunks (
                    id TEXT PRIMARY KEY,
                    document_id TEXT NOT NULL,
                    chunk_text TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    page_number INTEGER NOT NULL,
                    embedding BLOB,
                    char_count INTEGER,
                    word_count INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes for document_chunks
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON document_chunks(document_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_page_number ON document_chunks(page_number)")

            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS document_chunks_fts USING fts5(
                    chunk_id UNINDEXED,
                    document_id UNINDEXED,
                    chunk_text,
                    tokenize='unicode61'
                )
            """)
            conn.execute("""
                INSERT INTO document_chunks_fts(rowid, chunk_id, document_id, chunk_text)
                SELECT c.rowid, c.id, c.document_id, c.chunk_text
                FROM document_chunks c
                WHERE NOT EXISTS (
                    SELECT 1 FROM document_chunks_fts f WHERE f.chunk_id = c.id
                )
            """)
            
            conn.commit()
            print("✅ Document chunks table initialized for RAG")

    def _notify_library_changed(self, client_id: Optional[str] = None) -> None:
        try:
            from .semantic_cache import get_semantic_search_cache
            get_semantic_search_cache().mark_library_changed(client_id)
        except Exception as exc:
            print(f"⚠️ Failed to update semantic cache revision: {exc}")

    def _client_id_for_document(self, document_id: str) -> Optional[str]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT client_id FROM documents WHERE id = ?",
                (document_id,),
            )
            row = cursor.fetchone()
            return row[0] if row else None

    def _row_to_document(self, row: sqlite3.Row) -> Document:
        doc_data = dict(row)
        if doc_data.get('validation_result'):
            doc_data['validation_result'] = json.loads(doc_data['validation_result'])
        if doc_data.get('metadata'):
            doc_data['metadata'] = json.loads(doc_data['metadata'])
        if doc_data.get('tags'):
            doc_data['tags'] = json.loads(doc_data['tags'])

        doc_data['upload_date'] = datetime.fromisoformat(doc_data['upload_date'])
        if doc_data.get('last_uploaded'):
            doc_data['last_uploaded'] = datetime.fromisoformat(doc_data['last_uploaded'])
        if doc_data.get('last_opened'):
            doc_data['last_opened'] = datetime.fromisoformat(doc_data['last_opened'])
        if doc_data.get('last_accessed'):
            doc_data['last_accessed'] = datetime.fromisoformat(doc_data['last_accessed'])

        doc_data.pop('created_at', None)
        doc_data.pop('updated_at', None)
        return Document(**doc_data)
    
    def create_document(self,
                       filename: str,
                       original_name: str,
                       file_size: int,
                       file_path: str,
                       client_id: Optional[str] = None,
                       persona: Optional[str] = None,
                       job_role: Optional[str] = None,
                       validation_result: Optional[Dict[str, Any]] = None,
                       metadata: Optional[Dict[str, Any]] = None,
                       file_hash: Optional[str] = None) -> Document:
        """Create a new document record"""
        
        now = datetime.now()
        document = Document(
            id=str(uuid.uuid4()),
            filename=filename,
            original_name=original_name,
            upload_date=now,
            file_size=file_size,
            file_path=file_path,
            client_id=client_id,
            persona=persona,
            job_role=job_role,
            validation_result=validation_result,
            metadata=metadata,
            last_uploaded=now,  # Set upload time
            last_opened=None,   # Not opened yet
            file_hash=file_hash
        )
        
        with sqlite3.connect(self.db_path) as conn:
            # Check which columns exist
            cursor = conn.execute("PRAGMA table_info(documents)")
            existing_columns = {row[1] for row in cursor.fetchall()}

            # Build dynamic insert query based on available columns
            base_columns = [
                'id', 'filename', 'original_name', 'upload_date', 'file_size', 'file_path',
                'client_id', 'persona', 'job_role', 'validation_result', 'metadata'
            ]
            base_values = [
                document.id,
                document.filename,
                document.original_name,
                document.upload_date,
                document.file_size,
                document.file_path,
                document.client_id,
                document.persona,
                document.job_role,
                json.dumps(document.validation_result) if document.validation_result else None,
                json.dumps(document.metadata) if document.metadata else None
            ]

            # Add new columns if they exist
            if 'last_uploaded' in existing_columns:
                base_columns.append('last_uploaded')
                base_values.append(document.last_uploaded)
            if 'last_opened' in existing_columns:
                base_columns.append('last_opened')
                base_values.append(document.last_opened)
            if 'file_hash' in existing_columns:
                base_columns.append('file_hash')
                base_values.append(document.file_hash)

            # Build and execute query
            columns_str = ', '.join(base_columns)
            placeholders = ', '.join(['?'] * len(base_values))
            query = f"INSERT INTO documents ({columns_str}) VALUES ({placeholders})"

            conn.execute(query, base_values)
            conn.commit()
        self._notify_library_changed(client_id)
        
        return document
    
    def get_all_documents(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
        client_id: Optional[str] = None
    ) -> List[Document]:
        """Get documents with optional pagination and tenant filtering"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            params: List[Any] = []
            query = """
                SELECT * FROM documents
                WHERE status != 'deleted'
            """

            if client_id:
                query += " AND client_id = ?"
                params.append(client_id)

            query += """
                ORDER BY
                    CASE
                        WHEN last_opened IS NOT NULL THEN last_opened
                        ELSE upload_date
                    END DESC
            """

            if limit:
                query += " LIMIT ? OFFSET ?"
                params.extend([limit, offset])

            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            documents = []
            for row in rows:
                doc_data = dict(row)
                
                # Parse JSON fields
                if doc_data['validation_result']:
                    doc_data['validation_result'] = json.loads(doc_data['validation_result'])
                if doc_data['metadata']:
                    doc_data['metadata'] = json.loads(doc_data['metadata'])
                if doc_data['tags']:
                    doc_data['tags'] = json.loads(doc_data['tags'])
                
                # Convert timestamp strings to datetime objects
                doc_data['upload_date'] = datetime.fromisoformat(doc_data['upload_date'])
                if doc_data['last_uploaded']:
                    doc_data['last_uploaded'] = datetime.fromisoformat(doc_data['last_uploaded'])
                if doc_data['last_opened']:
                    doc_data['last_opened'] = datetime.fromisoformat(doc_data['last_opened'])
                if doc_data['last_accessed']:
                    doc_data['last_accessed'] = datetime.fromisoformat(doc_data['last_accessed'])
                
                # Remove extra fields not in Document model
                doc_data.pop('created_at', None)
                doc_data.pop('updated_at', None)
                
                documents.append(Document(**doc_data))
            
            return documents
    
    def get_document_by_id(self, document_id: str, client_id: Optional[str] = None) -> Optional[Document]:
        """Get a specific document by ID with optional tenant filtering"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            params: List[Any] = [document_id]
            query = "SELECT * FROM documents WHERE id = ? AND status != 'deleted'"

            if client_id:
                query += " AND client_id = ?"
                params.append(client_id)

            cursor = conn.execute(query, params)
            row = cursor.fetchone()

            if not row:
                return None

            return self._row_to_document(row)

    def get_document_by_filename(self, filename: str, client_id: Optional[str] = None) -> Optional[Document]:
        """Get a non-deleted document by stored filename with optional tenant filtering."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            params: List[Any] = [filename]
            query = "SELECT * FROM documents WHERE filename = ? AND status != 'deleted'"

            if client_id:
                query += " AND client_id = ?"
                params.append(client_id)

            cursor = conn.execute(query, params)
            row = cursor.fetchone()
            return self._row_to_document(row) if row else None

    def get_document_metadata(self, document_id: str) -> List[Dict[str, Any]]:
        """Get metadata/sections for a document"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT page, text, embedding_vector
            FROM document_sections
            WHERE document_id = ?
            ORDER BY page, section_index
            LIMIT 10
        """, (document_id,))

        rows = cursor.fetchall()
        metadata = []
        for row in rows:
            metadata.append({
                'page': row[0],
                'text': row[1],
                'embedding_vector': row[2]
            })
        return metadata

    def delete_document(self, document_id: str) -> bool:
        """Delete a document and all its related data"""
        try:
            cursor = self.conn.cursor()

            # Delete from document_sections first (foreign key constraint)
            cursor.execute("DELETE FROM document_sections WHERE document_id = ?", (document_id,))

            # Delete from documents table
            cursor.execute("DELETE FROM documents WHERE id = ?", (document_id,))

            # Check if document was actually deleted
            deleted_count = cursor.rowcount

            self.conn.commit()

            if deleted_count > 0:
                print(f"✅ Deleted document {document_id} and {cursor.rowcount} related sections")
                return True
            else:
                print(f"⚠️ Document {document_id} not found in database")
                return False

        except Exception as e:
            print(f"❌ Error deleting document {document_id}: {e}")
            self.conn.rollback()
            return False
    
    def update_document(
        self,
        document_id: str,
        client_id: Optional[str] = None,
        **updates
    ) -> bool:
        """Update document fields"""
        if not updates:
            return False
        
        # Handle JSON fields
        if 'validation_result' in updates and updates['validation_result']:
            updates['validation_result'] = json.dumps(updates['validation_result'])
        if 'metadata' in updates and updates['metadata']:
            updates['metadata'] = json.dumps(updates['metadata'])
        if 'tags' in updates and updates['tags']:
            updates['tags'] = json.dumps(updates['tags'])
        
        # Add updated_at timestamp if not explicitly provided
        updates.setdefault('updated_at', datetime.now())
        
        # Build dynamic query
        set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
        values = list(updates.values()) + [document_id]
        query = f"UPDATE documents SET {set_clause} WHERE id = ?"

        if client_id:
            query += " AND client_id = ?"
            values.append(client_id)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, values)
            conn.commit()
            updated = cursor.rowcount > 0

        if updated:
            self._notify_library_changed(client_id or self._client_id_for_document(document_id))
        return updated
    
    def delete_document(
        self,
        document_id: str,
        soft_delete: bool = True,
        client_id: Optional[str] = None
    ) -> bool:
        """Delete a document (soft delete by default)"""
        changed_client_id = client_id or self._client_id_for_document(document_id)
        with sqlite3.connect(self.db_path) as conn:
            params: List[Any]
            if soft_delete:
                query = "UPDATE documents SET status = 'deleted', updated_at = ? WHERE id = ?"
                params = [datetime.now(), document_id]
            else:
                query = "DELETE FROM documents WHERE id = ?"
                params = [document_id]

            if client_id:
                query += " AND client_id = ?"
                params.append(client_id)

            cursor = conn.execute(query, params)
            conn.commit()
            deleted = cursor.rowcount > 0

        if deleted:
            self._notify_library_changed(changed_client_id)
        return deleted

    def update_last_opened(self, document_id: str, client_id: Optional[str] = None) -> bool:
        """Update the last_opened timestamp for a document"""
        return self.update_document(
            document_id,
            client_id=client_id,
            last_opened=datetime.now(),
            updated_at=datetime.now()
        )

    def get_documents_by_client(
        self,
        client_id: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Document]:
        """Get documents for a specific client"""
        return self.get_all_documents(limit=limit, offset=offset, client_id=client_id)
    
    def search_documents(
        self,
        query: str,
        fields: List[str] = None,
        client_id: Optional[str] = None
    ) -> List[Document]:
        """Search documents by text in specified fields"""
        if not fields:
            fields = ['original_name', 'filename', 'persona', 'job_role']
        
        documents = self.get_all_documents(client_id=client_id)
        results = []
        
        query_lower = query.lower()
        for doc in documents:
            for field in fields:
                field_value = getattr(doc, field, '')
                if field_value and query_lower in field_value.lower():
                    results.append(doc)
                    break
        
        return results
    
    def get_document_stats(self, client_id: Optional[str] = None) -> Dict[str, Any]:
        """Get database statistics"""
        with sqlite3.connect(self.db_path) as conn:
            params: List[Any] = []
            query = """
                SELECT
                    COUNT(*) as total_documents,
                    COUNT(CASE WHEN status = 'uploaded' THEN 1 END) as uploaded,
                    COUNT(CASE WHEN processing_status = 'completed' THEN 1 END) as processed,
                    COUNT(CASE WHEN last_opened IS NOT NULL THEN 1 END) as opened_documents,
                    SUM(file_size) as total_size
                FROM documents
                WHERE status != 'deleted'
            """

            if client_id:
                query += " AND client_id = ?"
                params.append(client_id)

            cursor = conn.execute(query, params)
            row = cursor.fetchone()

            return {
                'total_documents': row[0],
                'uploaded_documents': row[1],
                'processed_documents': row[2],
                'opened_documents': row[3],
                'total_size_bytes': row[4] or 0
            }

    def find_duplicate_by_hash(self, file_hash: str, client_id: Optional[str] = None) -> Optional[Document]:
        """Find document with matching hash"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM documents WHERE file_hash = ? AND status != 'deleted'"
            params: List[Any] = [file_hash]
            if client_id:
                query += " AND client_id = ?"
                params.append(client_id)

            cursor = conn.execute(query, params)
            row = cursor.fetchone()

            if row:
                doc_data = dict(row)

                # Parse JSON fields
                if doc_data['validation_result']:
                    doc_data['validation_result'] = json.loads(doc_data['validation_result'])
                if doc_data['metadata']:
                    doc_data['metadata'] = json.loads(doc_data['metadata'])
                if doc_data['tags']:
                    doc_data['tags'] = json.loads(doc_data['tags'])

                # Convert timestamp strings to datetime objects
                doc_data['upload_date'] = datetime.fromisoformat(doc_data['upload_date'])
                if doc_data['last_uploaded']:
                    doc_data['last_uploaded'] = datetime.fromisoformat(doc_data['last_uploaded'])
                if doc_data['last_opened']:
                    doc_data['last_opened'] = datetime.fromisoformat(doc_data['last_opened'])
                if doc_data['last_accessed']:
                    doc_data['last_accessed'] = datetime.fromisoformat(doc_data['last_accessed'])

                # Remove extra fields
                doc_data.pop('created_at', None)
                doc_data.pop('updated_at', None)

                return Document(**doc_data)

            return None

    def update_last_uploaded(self, document_id: str, client_id: Optional[str] = None) -> bool:
        """Update last uploaded timestamp"""
        return self.update_document(
            document_id,
            client_id=client_id,
            last_uploaded=datetime.now()
        )

    def update_last_opened(self, document_id: str, client_id: Optional[str] = None) -> bool:
        """Update last opened timestamp"""
        return self.update_document(
            document_id,
            client_id=client_id,
            last_opened=datetime.now()
        )

    def get_documents_sorted(
        self,
        sort_by: str = 'upload_date',
        sort_order: str = 'desc',
        limit: Optional[int] = None,
        client_id: Optional[str] = None
    ) -> List[Document]:
        """
        Get documents with sorting options

        Args:
            sort_by: 'upload_date', 'last_uploaded', 'last_opened', 'original_name', 'file_size'
            sort_order: 'asc' or 'desc'
            limit: Maximum number of documents to return
        """
        valid_sort_fields = {
            'upload_date': 'upload_date',
            'last_uploaded': 'last_uploaded',
            'last_opened': 'last_opened',
            'name': 'original_name',
            'size': 'file_size',
            'recently_opened': 'last_opened',
            'recently_uploaded': 'last_uploaded'
        }

        if sort_by not in valid_sort_fields:
            sort_by = 'upload_date'

        db_field = valid_sort_fields[sort_by]
        order = 'DESC' if sort_order.lower() == 'desc' else 'ASC'

        # Handle NULL values for last_opened and last_uploaded
        if db_field in ['last_opened', 'last_uploaded']:
            order_clause = f"{db_field} IS NULL, {db_field} {order}"
        else:
            order_clause = f"{db_field} {order}"

        query = f"""
            SELECT * FROM documents
            WHERE status != 'deleted'
        """
        params: List[Any] = []

        if client_id:
            query += " AND client_id = ?"
            params.append(client_id)

        query += f" ORDER BY {order_clause}"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

            documents = []
            for row in rows:
                doc_data = dict(row)

                # Parse JSON fields
                if doc_data['validation_result']:
                    doc_data['validation_result'] = json.loads(doc_data['validation_result'])
                if doc_data['metadata']:
                    doc_data['metadata'] = json.loads(doc_data['metadata'])
                if doc_data['tags']:
                    doc_data['tags'] = json.loads(doc_data['tags'])

                # Convert timestamp strings to datetime objects
                doc_data['upload_date'] = datetime.fromisoformat(doc_data['upload_date'])
                if doc_data['last_uploaded']:
                    doc_data['last_uploaded'] = datetime.fromisoformat(doc_data['last_uploaded'])
                if doc_data['last_opened']:
                    doc_data['last_opened'] = datetime.fromisoformat(doc_data['last_opened'])
                if doc_data['last_accessed']:
                    doc_data['last_accessed'] = datetime.fromisoformat(doc_data['last_accessed'])

                # Remove extra fields
                doc_data.pop('created_at', None)
                doc_data.pop('updated_at', None)

                documents.append(Document(**doc_data))

            return documents
    
    def store_chunk(
        self,
        document_id: str,
        chunk_text: str,
        chunk_index: int,
        page_number: int,
        embedding: Optional[List[float]] = None,
        char_count: Optional[int] = None,
        word_count: Optional[int] = None
    ) -> str:
        """
        Store a document chunk in the database
        
        Returns:
            chunk_id: ID of the stored chunk
        """
        chunk_id = str(uuid.uuid4())
        
        # Convert embedding to binary if provided
        embedding_blob = None
        if embedding:
            import pickle
            embedding_blob = pickle.dumps(embedding)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO document_chunks 
                (id, document_id, chunk_text, chunk_index, page_number, embedding, char_count, word_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (chunk_id, document_id, chunk_text, chunk_index, page_number, 
                  embedding_blob, char_count, word_count))
            conn.execute(
                """
                INSERT INTO document_chunks_fts(rowid, chunk_id, document_id, chunk_text)
                VALUES (?, ?, ?, ?)
                """,
                (cursor.lastrowid, chunk_id, document_id, chunk_text),
            )
            conn.commit()
        self._notify_library_changed(self._client_id_for_document(document_id))
        
        return chunk_id
    
    def get_chunks_by_document(self, document_id: str, client_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all chunks for a document"""
        document = self.get_document_by_id(document_id, client_id=client_id) if client_id else self.get_document_by_id(document_id)
        if not document:
            return []

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT id, document_id, chunk_text, chunk_index, page_number, 
                       char_count, word_count, created_at
                FROM document_chunks
                WHERE document_id = ?
                ORDER BY chunk_index
            """, (document_id,))
            
            chunks = []
            for row in cursor.fetchall():
                chunk_data = dict(row)
                if chunk_data['created_at']:
                    chunk_data['created_at'] = datetime.fromisoformat(chunk_data['created_at'])
                chunks.append(chunk_data)
            
            return chunks
    
    def delete_chunks_by_document(self, document_id: str, client_id: Optional[str] = None) -> int:
        """Delete all chunks for a document"""
        document = self.get_document_by_id(document_id, client_id=client_id) if client_id else self.get_document_by_id(document_id)
        if not document:
            return 0

        changed_client_id = client_id or document.client_id
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "DELETE FROM document_chunks_fts WHERE document_id = ?",
                (document_id,),
            )
            cursor = conn.execute(
                "DELETE FROM document_chunks WHERE document_id = ?",
                (document_id,)
            )
            conn.commit()
            deleted = cursor.rowcount

        if deleted:
            self._notify_library_changed(changed_client_id)
        return deleted

    def search_chunks_bm25(
        self,
        query: str,
        limit: int = 20,
        document_id: Optional[str] = None,
        exclude_document_id: Optional[str] = None,
        client_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search indexed chunks with SQLite FTS5 BM25 ranking."""
        fts_query = self._fts_query(query)
        if not fts_query:
            return []

        limit = max(1, min(int(limit or 1), 100))
        sql = """
            SELECT
                c.id AS chunk_id,
                c.document_id,
                c.chunk_text,
                c.chunk_index,
                c.page_number,
                d.client_id,
                d.filename,
                d.original_name,
                d.file_path,
                d.upload_date,
                d.last_uploaded,
                d.last_opened,
                d.last_accessed,
                bm25(document_chunks_fts) AS bm25_rank
            FROM document_chunks_fts
            JOIN document_chunks c ON c.id = document_chunks_fts.chunk_id
            JOIN documents d ON d.id = c.document_id
            WHERE document_chunks_fts MATCH ?
              AND d.status != 'deleted'
        """
        params: List[Any] = [fts_query]

        if document_id:
            sql += " AND c.document_id = ?"
            params.append(document_id)
        if exclude_document_id:
            sql += " AND c.document_id != ?"
            params.append(exclude_document_id)
        if client_id:
            sql += " AND d.client_id = ?"
            params.append(client_id)

        sql += " ORDER BY bm25_rank ASC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = [dict(row) for row in conn.execute(sql, params).fetchall()]

        if not rows:
            return []

        positive_scores = []
        for row in rows:
            rank = float(row.get("bm25_rank") or 0.0)
            positive_scores.append(-rank if rank < 0 else 1.0 / (1.0 + rank))

        max_score = max(positive_scores) if positive_scores else 0.0
        results: List[Dict[str, Any]] = []
        for row, positive_score in zip(rows, positive_scores):
            keyword_score = (positive_score / max_score) if max_score > 0 else 0.0
            row["metadata"] = {
                "document_name": row.get("original_name") or row.get("filename") or "Unknown Document",
                "filename": row.get("filename"),
                "original_name": row.get("original_name"),
                "file_path": row.get("file_path"),
                "upload_date": row.get("upload_date"),
                "last_uploaded": row.get("last_uploaded") or row.get("upload_date"),
                "last_opened": row.get("last_opened"),
                "last_accessed": row.get("last_accessed"),
                "retrieval_source": "bm25",
                "bm25_rank": round(float(row.get("bm25_rank") or 0.0), 6),
                "bm25_score": round(float(positive_score), 6),
                "keyword_score": round(float(keyword_score), 4),
            }
            results.append(row)

        return results

    def _fts_query(self, query: str) -> str:
        terms = re.findall(r"[A-Za-z0-9]{2,}", query or "")
        if not terms:
            return ""
        return " OR ".join(f'"{term}"' for term in terms[:24])

    def get_library_revision(self, client_id: Optional[str] = None) -> str:
        """Return a stable revision hash for the active document library.

        Retrieval cache entries use this value as part of their scope. Any
        upload, metadata update, soft/hard delete, or chunk reingestion changes
        the payload and therefore stops stale cache entries from matching.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            params: List[Any] = []
            where_clause = "WHERE status != 'deleted'"
            if client_id:
                where_clause += " AND client_id = ?"
                params.append(client_id)

            document_rows = conn.execute(
                f"""
                SELECT
                    id,
                    filename,
                    original_name,
                    status,
                    processing_status,
                    upload_date,
                    last_uploaded,
                    last_opened,
                    last_accessed,
                    updated_at,
                    file_size,
                    COALESCE(metadata, '') AS metadata
                FROM documents
                {where_clause}
                ORDER BY id
                """,
                params,
            ).fetchall()

            chunk_rows = conn.execute(
                f"""
                SELECT
                    d.id AS document_id,
                    COUNT(c.id) AS chunk_count,
                    COALESCE(MAX(c.created_at), '') AS latest_chunk_at
                FROM documents d
                LEFT JOIN document_chunks c ON c.document_id = d.id
                {where_clause.replace('status', 'd.status').replace('client_id', 'd.client_id')}
                GROUP BY d.id
                ORDER BY d.id
                """,
                params,
            ).fetchall()

        payload = {
            "client_id": client_id or "",
            "documents": [dict(row) for row in document_rows],
            "chunks": [dict(row) for row in chunk_rows],
        }
        serialized = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    
    def get_chunk_count(self, document_id: Optional[str] = None, client_id: Optional[str] = None) -> int:
        """Get total chunk count, optionally filtered by document"""
        with sqlite3.connect(self.db_path) as conn:
            if document_id:
                if client_id:
                    cursor = conn.execute(
                        """
                        SELECT COUNT(*)
                        FROM document_chunks c
                        JOIN documents d ON d.id = c.document_id
                        WHERE c.document_id = ?
                          AND d.client_id = ?
                          AND d.status != 'deleted'
                        """,
                        (document_id, client_id)
                    )
                else:
                    cursor = conn.execute(
                        "SELECT COUNT(*) FROM document_chunks WHERE document_id = ?",
                        (document_id,)
                    )
            elif client_id:
                cursor = conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM document_chunks c
                    JOIN documents d ON d.id = c.document_id
                    WHERE d.client_id = ?
                      AND d.status != 'deleted'
                    """,
                    (client_id,)
                )
            else:
                cursor = conn.execute("SELECT COUNT(*) FROM document_chunks")
            
            return cursor.fetchone()[0]

# Global database instance
db = DocumentDatabase()
