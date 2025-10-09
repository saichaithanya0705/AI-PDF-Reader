# app/models.py
from pydantic import BaseModel
from typing import List

class Section(BaseModel):
    doc_id: str
    doc_filename: str
    section_title: str
    content: str
    page_number: int
    level: str

class SectionHighlight(BaseModel):
    """
    A simplified model for sending highlight data to the frontend.
    The Adobe API needs a page number and coordinates. We'll simulate this.
    """
    doc_id: str
    page: int
    snippet: str

class WebSocketMessage(BaseModel):
    """Defines the structure for messages sent over WebSocket."""
    type: str  # e.g., "progress", "section_highlight"
    job_id: str
    data: dict

class RelevantSection(BaseModel):
    id: str
    title: str
    snippet: str
    page: int
    relevance: float
    documentId: str
    documentName: str