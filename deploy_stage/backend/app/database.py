"""
Database models and operations for PDF document management
"""

import sqlite3
import uuid
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
            
            conn.commit()
            print("✅ Document chunks table initialized for RAG")
    
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

            doc_data = dict(row)
            if doc_data['validation_result']:
                doc_data['validation_result'] = json.loads(doc_data['validation_result'])
            if doc_data['metadata']:
                doc_data['metadata'] = json.loads(doc_data['metadata'])
            if doc_data['tags']:
                doc_data['tags'] = json.loads(doc_data['tags'])

            doc_data['upload_date'] = datetime.fromisoformat(doc_data['upload_date'])
            if doc_data['last_uploaded']:
                doc_data['last_uploaded'] = datetime.fromisoformat(doc_data['last_uploaded'])
            if doc_data['last_opened']:
                doc_data['last_opened'] = datetime.fromisoformat(doc_data['last_opened'])
            if doc_data['last_accessed']:
                doc_data['last_accessed'] = datetime.fromisoformat(doc_data['last_accessed'])

            doc_data.pop('created_at', None)
            doc_data.pop('updated_at', None)

            return Document(**doc_data)

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
            return cursor.rowcount > 0
    
    def delete_document(
        self,
        document_id: str,
        soft_delete: bool = True,
        client_id: Optional[str] = None
    ) -> bool:
        """Delete a document (soft delete by default)"""
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
            return cursor.rowcount > 0

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

    def find_duplicate_by_hash(self, file_hash: str) -> Optional[Document]:
        """Find document with matching hash"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM documents WHERE file_hash = ? AND status != 'deleted'",
                (file_hash,)
            )
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
            conn.execute("""
                INSERT INTO document_chunks 
                (id, document_id, chunk_text, chunk_index, page_number, embedding, char_count, word_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (chunk_id, document_id, chunk_text, chunk_index, page_number, 
                  embedding_blob, char_count, word_count))
            conn.commit()
        
        return chunk_id
    
    def get_chunks_by_document(self, document_id: str) -> List[Dict[str, Any]]:
        """Get all chunks for a document"""
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
    
    def delete_chunks_by_document(self, document_id: str) -> int:
        """Delete all chunks for a document"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "DELETE FROM document_chunks WHERE document_id = ?",
                (document_id,)
            )
            conn.commit()
            return cursor.rowcount
    
    def get_chunk_count(self, document_id: Optional[str] = None) -> int:
        """Get total chunk count, optionally filtered by document"""
        with sqlite3.connect(self.db_path) as conn:
            if document_id:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM document_chunks WHERE document_id = ?",
                    (document_id,)
                )
            else:
                cursor = conn.execute("SELECT COUNT(*) FROM document_chunks")
            
            return cursor.fetchone()[0]

# Global database instance
db = DocumentDatabase()

