"""
Section Highlighting Service for Adobe Hackathon
Provides coordinates and highlighting data for PDF sections
"""

import fitz  # PyMuPDF
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path
import re
import numpy as np
from dataclasses import dataclass


@dataclass
class HighlightBox:
    """Represents a highlight box with coordinates"""
    page: int
    x: float
    y: float
    width: float
    height: float
    text: str
    confidence: float


@dataclass
class SectionHighlight:
    """Represents a highlighted section with metadata"""
    section_id: str
    title: str
    snippet: str
    page: int
    boxes: List[HighlightBox]
    relevance: float


class SectionHighlighter:
    """Service for finding and highlighting sections in PDFs"""
    
    def __init__(self):
        self.confidence_threshold = 0.7
    
    def find_section_coordinates(self, pdf_path: str, section_text: str, page_num: int = None) -> List[HighlightBox]:
        """
        Find coordinates of text sections in PDF for highlighting
        
        Args:
            pdf_path: Path to the PDF file
            section_text: Text to find and highlight
            page_num: Specific page to search (None for all pages)
        
        Returns:
            List of HighlightBox objects with coordinates
        """
        try:
            doc = fitz.open(pdf_path)
            highlight_boxes = []
            
            # Determine pages to search
            pages_to_search = [page_num] if page_num is not None else range(len(doc))
            
            for page_idx in pages_to_search:
                if page_idx >= len(doc):
                    continue
                    
                page = doc[page_idx]
                
                # Search for exact text matches
                text_instances = page.search_for(section_text[:100])  # Limit search text length
                
                for inst in text_instances:
                    highlight_boxes.append(HighlightBox(
                        page=page_idx + 1,  # 1-based page numbering
                        x=float(inst.x0),
                        y=float(inst.y0),
                        width=float(inst.x1 - inst.x0),
                        height=float(inst.y1 - inst.y0),
                        text=section_text[:100],
                        confidence=1.0  # Exact match
                    ))
                
                # If no exact matches, try fuzzy matching
                if not text_instances:
                    fuzzy_boxes = self._fuzzy_text_search(page, section_text, page_idx + 1)
                    highlight_boxes.extend(fuzzy_boxes)
            
            doc.close()
            return highlight_boxes
            
        except Exception as e:
            print(f"Error finding section coordinates: {e}")
            return []
    
    def _fuzzy_text_search(self, page, target_text: str, page_num: int) -> List[HighlightBox]:
        """
        Perform fuzzy text search when exact match fails
        """
        try:
            # Get all text blocks from the page
            text_dict = page.get_text("dict")
            highlight_boxes = []
            
            # Extract words and their positions
            words_with_positions = []
            for block in text_dict["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            text = span["text"].strip()
                            if text:
                                words_with_positions.append({
                                    "text": text,
                                    "bbox": span["bbox"],
                                    "font_size": span["size"]
                                })
            
            # Look for partial matches
            target_words = target_text.lower().split()[:5]  # First 5 words
            
            for i, word_data in enumerate(words_with_positions):
                word_text = word_data["text"].lower()
                
                # Check if this word starts a potential match
                if any(target_word in word_text for target_word in target_words):
                    # Try to match a sequence of words
                    match_score = self._calculate_match_score(
                        words_with_positions[i:i+len(target_words)], 
                        target_words
                    )
                    
                    if match_score > self.confidence_threshold:
                        # Create highlight box for the matched sequence
                        bbox = self._get_sequence_bbox(words_with_positions[i:i+len(target_words)])
                        
                        highlight_boxes.append(HighlightBox(
                            page=page_num,
                            x=float(bbox[0]),
                            y=float(bbox[1]),
                            width=float(bbox[2] - bbox[0]),
                            height=float(bbox[3] - bbox[1]),
                            text=target_text[:100],
                            confidence=match_score
                        ))
            
            return highlight_boxes
            
        except Exception as e:
            print(f"Error in fuzzy text search: {e}")
            return []
    
    def _calculate_match_score(self, word_sequence: List[Dict], target_words: List[str]) -> float:
        """Calculate similarity score between word sequence and target"""
        if not word_sequence or not target_words:
            return 0.0
        
        matches = 0
        total = min(len(word_sequence), len(target_words))
        
        for i in range(total):
            word_text = word_sequence[i]["text"].lower()
            target_word = target_words[i].lower()
            
            # Exact match
            if word_text == target_word:
                matches += 1
            # Partial match
            elif target_word in word_text or word_text in target_word:
                matches += 0.5
        
        return matches / total if total > 0 else 0.0
    
    def _get_sequence_bbox(self, word_sequence: List[Dict]) -> Tuple[float, float, float, float]:
        """Get bounding box for a sequence of words"""
        if not word_sequence:
            return (0, 0, 0, 0)
        
        min_x = min(word["bbox"][0] for word in word_sequence)
        min_y = min(word["bbox"][1] for word in word_sequence)
        max_x = max(word["bbox"][2] for word in word_sequence)
        max_y = max(word["bbox"][3] for word in word_sequence)
        
        return (min_x, min_y, max_x, max_y)
    
    def get_section_highlights(self, document_id: str, page: int, related_sections: List[Dict]) -> List[SectionHighlight]:
        """
        Get highlight data for related sections
        
        Args:
            document_id: ID of the current document
            page: Current page number
            related_sections: List of related sections from recommendations API
        
        Returns:
            List of SectionHighlight objects
        """
        highlights = []
        
        # Find the PDF file path for this document
        pdf_path = self._find_pdf_path(document_id)
        if not pdf_path:
            return highlights
        
        for section in related_sections:
            try:
                # Get coordinates for this section
                boxes = self.find_section_coordinates(
                    pdf_path, 
                    section.get("snippet", ""), 
                    section.get("page")
                )
                
                if boxes:
                    highlights.append(SectionHighlight(
                        section_id=section.get("id", ""),
                        title=section.get("title", ""),
                        snippet=section.get("snippet", ""),
                        page=section.get("page", 1),
                        boxes=boxes,
                        relevance=section.get("relevance", 0.0)
                    ))
                    
            except Exception as e:
                print(f"Error creating highlight for section {section.get('id')}: {e}")
                continue
        
        return highlights
    
    def _find_pdf_path(self, document_id: str) -> Optional[str]:
        """Find the file path for a document ID"""
        # Look in the docs directory for files with this document ID
        docs_dir = Path("data/docs")
        if docs_dir.exists():
            for file_path in docs_dir.glob(f"{document_id}_*"):
                if file_path.suffix.lower() == '.pdf':
                    return str(file_path)
        return None
    
    def create_highlight_overlay_data(self, highlights: List[SectionHighlight]) -> Dict[str, Any]:
        """
        Create overlay data for frontend highlighting
        
        Returns:
            Dictionary with highlight data formatted for Adobe PDF Embed API
        """
        overlay_data = {
            "highlights": [],
            "annotations": []
        }
        
        for highlight in highlights:
            for box in highlight.boxes:
                # Format for Adobe PDF Embed API
                highlight_data = {
                    "id": highlight.section_id,
                    "page": box.page,
                    "coordinates": {
                        "x": box.x,
                        "y": box.y,
                        "width": box.width,
                        "height": box.height
                    },
                    "color": self._get_highlight_color(highlight.relevance),
                    "opacity": min(0.3 + (highlight.relevance * 0.4), 0.7),
                    "title": highlight.title,
                    "snippet": highlight.snippet,
                    "relevance": highlight.relevance,
                    "confidence": box.confidence
                }
                
                overlay_data["highlights"].append(highlight_data)
        
        return overlay_data
    
    def _get_highlight_color(self, relevance: float) -> str:
        """Get color based on relevance score"""
        if relevance >= 0.8:
            return "#00ff88"  # High relevance - green
        elif relevance >= 0.6:
            return "#ffaa00"  # Medium relevance - orange
        else:
            return "#ff6b6b"  # Lower relevance - red
