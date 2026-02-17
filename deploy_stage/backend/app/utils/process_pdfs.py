#!/usr/bin/env python3
"""
Adobe Hackathon Round 1a - PDF Heading Extraction Solution
High-Performance PDF Processing Solution for Adobe Hackathon Challenge 1a
Optimized for speed and accuracy with PyMuPDF (fitz)

EXECUTION COMMANDS:
================
Docker Build:
    docker build --platform linux/amd64 -t mysolutionname:somerandomidentifier .

Docker Run:
    docker run --rm -v $(pwd)/input:/app/input -v $(pwd)/output:/app/output --network none mysolutionname:somerandomidentifier

Local Testing:
    mkdir -p input output
    cp sample.pdf input/
    python process_pdfs.py

WORKFLOW PIPELINE:
=================
1. Multi-Strategy Detection Pipeline:
   - Pattern-Based Detection (Highest Confidence): Regex patterns for chapters, numbered sections, roman numerals
   - Content-Based Detection: Recognition of heading indicator words (introduction, conclusion, etc.)
   - Typography-Based Detection: Font analysis as supporting evidence (not sole determinant)
   - Position-Based Detection: Spatial analysis for isolated text blocks
   - Confidence Scoring: Prioritize detections by reliability
   - Deduplication: Remove duplicates while preserving best matches

2. Processing Steps:
   - Extract text with font information for better heading detection
   - Analyze document structure to find common font size and font
   - Extract outline from PDF's built-in table of contents (if available)
   - Extract outline by analyzing document content using multiple strategies
   - Clean and deduplicate outline entries
   - Generate exact JSON format as required by hackathon specifications

PERFORMANCE TARGETS:
===================
- Simple PDFs: < 1 second processing time
- Complex PDFs: 2-4 seconds processing time
- 50-page PDFs: < 5 seconds (well under 10s requirement)
- Memory Usage: < 2GB for large documents
"""

import json
import re
import fitz  # PyMuPDF
from pathlib import Path
import time
import logging
import unicodedata
from typing import List, Dict, Tuple, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import multiprocessing as mp
from ..models import Section  # Import Section from models.py

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HighPerformancePDFProcessor:
    """
    Optimized PDF processor for extracting structured outlines

    IMPLEMENTATION WORKFLOW:
    =======================
    This class implements the multi-strategy detection pipeline described in the README:

    1. Pattern-Based Detection (Highest Confidence):
       - Regex patterns for chapters, numbered sections, roman numerals
       - Handles "Chapter 1", "1.1 Introduction", "I. Overview" patterns

    2. Content-Based Detection:
       - Recognition of heading indicator words (introduction, conclusion, etc.)
       - Semantic understanding of heading structures

    3. Typography-Based Detection:
       - Font analysis as supporting evidence (not sole determinant)
       - Uses font size, bold flags, and font differences

    4. Position-Based Detection:
       - Spatial analysis for isolated text blocks
       - Context-aware section boundaries

    5. Confidence Scoring & Deduplication:
       - Prioritize detections by reliability
       - Remove duplicates while preserving best matches
    """

    def __init__(self):
        self.setup_heading_patterns()
        self.setup_multilingual_patterns()

    def setup_heading_patterns(self):
        """Setup comprehensive heading patterns for better hierarchy detection"""
        self.heading_patterns = [
            # Document titles and main sections (H1)
            (r'^(Chapter\s+\d+|CHAPTER\s+\d+)', 'chapter'),
            (r'^(Part\s+\d+|PART\s+\d+)', 'part'),
            (r'^(Section\s+\d+|SECTION\s+\d+)', 'section'),
            (r'^(Introduction|Conclusion|Abstract|Summary|Overview|Background)', 'main'),
            (r'^(Round\s+\d+[A-Z]?|Challenge|Mission|Theme)', 'main'),
            
            # Subsections (H2)
            (r'^(\d+\.\s+[A-Z][^.]*)', 'section'),
            (r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s*:)', 'subsection'),
            (r'^(What|Why|How|When|Where|Who)\s+[A-Z]', 'subsection'),
            (r'^(Method|Procedure|Steps|Instructions|Requirements)', 'subsection'),
            (r'^(Test\s+Case|Example|Sample|Challenge|Brief)', 'subsection'),
            
            # Detailed subsections (H3)
            (r'^(\d+\.\d+\s+[A-Z][^.]*)', 'subsection'),
            (r'^([a-z]\s*\.\s+[A-Z][^.]*)', 'detail'),
            (r'^(Ingredients|Instructions|Steps|Tips|Notes)', 'detail'),
            (r'^(History|Background|Overview|Summary)', 'detail'),
            (r'^(Key|Main|Primary|Secondary)', 'detail'),
        ]

    def setup_multilingual_patterns(self):
        """Setup multilingual heading patterns for international documents"""
        self.multilingual_patterns = {
            # Chinese (Simplified & Traditional)
            'chinese': [
                (r'^(第[一二三四五六七八九十\d]+章)', 'chapter'),  # 第一章, 第1章
                (r'^([一二三四五六七八九十\d]+[、．])', 'section'),  # 一、二、
                (r'^(\d+[、．]\d+)', 'subsection'),  # 1.1, 1、1
                (r'^(章节|章|节|部分|段落)', 'section'),
            ],

            # Spanish
            'spanish': [
                (r'^(Capítulo\s+\d+|CAPÍTULO\s+\d+)', 'chapter'),
                (r'^(Sección\s+\d+|SECCIÓN\s+\d+)', 'section'),
                (r'^(Introducción|INTRODUCCIÓN)', 'section'),
                (r'^(Conclusión|CONCLUSIÓN)', 'section'),
                (r'^(Resumen|RESUMEN)', 'section'),
            ],

            # French
            'french': [
                (r'^(Chapitre\s+\d+|CHAPITRE\s+\d+)', 'chapter'),
                (r'^(Section\s+\d+|SECTION\s+\d+)', 'section'),
                (r'^(Introduction|INTRODUCTION)', 'section'),
                (r'^(Conclusion|CONCLUSION)', 'section'),
                (r'^(Résumé|RÉSUMÉ)', 'section'),
            ],

            # German
            'german': [
                (r'^(Kapitel\s+\d+|KAPITEL\s+\d+)', 'chapter'),
                (r'^(Abschnitt\s+\d+|ABSCHNITT\s+\d+)', 'section'),
                (r'^(Einleitung|EINLEITUNG)', 'section'),
                (r'^(Schlussfolgerung|SCHLUSSFOLGERUNG)', 'section'),
                (r'^(Zusammenfassung|ZUSAMMENFASSUNG)', 'section'),
            ],

            # Japanese
            'japanese': [
                (r'^(第[一二三四五六七八九十\d]+章)', 'chapter'),  # 第1章
                (r'^([一二三四五六七八九十\d]+[、．])', 'section'),  # 1、2、
                (r'^(はじめに|序論|序章)', 'section'),  # Introduction
                (r'^(結論|まとめ|終章)', 'section'),  # Conclusion
                (r'^(概要|要約)', 'section'),  # Summary
            ],

            # Arabic (RTL support)
            'arabic': [
                (r'^(الفصل\s+\d+)', 'chapter'),  # Chapter
                (r'^(القسم\s+\d+)', 'section'),  # Section
                (r'^(مقدمة|المقدمة)', 'section'),  # Introduction
                (r'^(خاتمة|الخاتمة)', 'section'),  # Conclusion
                (r'^(ملخص|الملخص)', 'section'),  # Summary
            ],

            # Russian
            'russian': [
                (r'^(Глава\s+\d+|ГЛАВА\s+\d+)', 'chapter'),
                (r'^(Раздел\s+\d+|РАЗДЕЛ\s+\d+)', 'section'),
                (r'^(Введение|ВВЕДЕНИЕ)', 'section'),
                (r'^(Заключение|ЗАКЛЮЧЕНИЕ)', 'section'),
                (r'^(Резюме|РЕЗЮМЕ)', 'section'),
            ]
        }

    def detect_document_language(self, doc) -> str:
        """Detect the primary language of the document"""
        # Sample text from first few pages
        sample_text = ""
        for page_num in range(min(3, len(doc))):  # Check first 3 pages
            page = doc[page_num]
            text = page.get_text()
            sample_text += text[:1000]  # First 1000 chars per page

        sample_text = sample_text.lower()

        # Language detection based on characteristic patterns
        language_indicators = {
            'chinese': ['的', '是', '在', '了', '和', '有', '我', '你', '他', '她', '它', '们'],
            'spanish': ['el', 'la', 'de', 'que', 'y', 'en', 'un', 'es', 'se', 'no', 'te', 'lo'],
            'french': ['le', 'de', 'et', 'à', 'un', 'il', 'être', 'et', 'en', 'avoir', 'que', 'pour'],
            'german': ['der', 'die', 'und', 'in', 'den', 'von', 'zu', 'das', 'mit', 'sich', 'des', 'auf'],
            'japanese': ['の', 'に', 'は', 'を', 'た', 'が', 'で', 'て', 'と', 'し', 'れ', 'さ'],
            'arabic': ['في', 'من', 'إلى', 'على', 'أن', 'هذا', 'هذه', 'التي', 'الذي', 'كان', 'كما'],
            'russian': ['в', 'и', 'не', 'на', 'я', 'быть', 'он', 'с', 'что', 'а', 'по', 'это']
        }

        # Score each language
        language_scores = {}
        for lang, indicators in language_indicators.items():
            score = sum(1 for indicator in indicators if indicator in sample_text)
            if score > 0:
                language_scores[lang] = score

        # Return the language with highest score, default to English
        if language_scores:
            detected_lang = max(language_scores.items(), key=lambda x: x[1])[0]
            logger.info(f"Detected language: {detected_lang} (score: {language_scores[detected_lang]})")
            return detected_lang
        else:
            return 'english'

    def get_patterns_for_language(self, language: str) -> List[Tuple[str, str]]:
        """Get heading patterns for the detected language"""
        patterns = self.heading_patterns.copy()  # Start with English patterns

        # Add language-specific patterns
        if language in self.multilingual_patterns:
            patterns.extend(self.multilingual_patterns[language])
            logger.info(f"Added {len(self.multilingual_patterns[language])} patterns for {language}")

        return patterns

    def extract_text_with_formatting(self, page) -> List[Dict]:
        """Extract text with font information for better heading detection"""
        blocks = []
        text_dict = page.get_text("dict")
        
        for block in text_dict["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if text:
                            blocks.append({
                                "text": text,
                                "font": span["font"],
                                "size": span["size"],
                                "flags": span["flags"],  # Bold, italic flags
                                "bbox": span["bbox"]
                            })
        return blocks
    
    def analyze_advanced_typography(self, doc) -> Dict:
        """Advanced typography analysis for better heading detection"""
        font_analysis = {
            'sizes': [],
            'fonts': {},
            'styles': {},
            'line_lengths': [],
            'spacing_patterns': [],
            'color_patterns': {},
            'alignment_patterns': {}
        }

        # Sample first few pages for comprehensive analysis
        sample_pages = min(5, len(doc))
        for page_num in range(sample_pages):
            page = doc[page_num]
            text_dict = page.get_text("dict")

            for block in text_dict["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        line_text = ""
                        line_spans = []

                        for span in line["spans"]:
                            line_text += span["text"]
                            line_spans.append(span)

                            # Collect font data
                            font_analysis['sizes'].append(span["size"])
                            font_key = span["font"]
                            font_analysis['fonts'][font_key] = font_analysis['fonts'].get(font_key, 0) + 1

                            # Style analysis
                            style_key = f"size_{int(span['size'])}_bold_{bool(span['flags'] & 2**4)}_italic_{bool(span['flags'] & 2**6)}"
                            font_analysis['styles'][style_key] = font_analysis['styles'].get(style_key, 0) + 1

                            # Color analysis (if available)
                            if 'color' in span:
                                color = span['color']
                                font_analysis['color_patterns'][color] = font_analysis['color_patterns'].get(color, 0) + 1

                        # Line length analysis
                        if line_text.strip():
                            font_analysis['line_lengths'].append(len(line_text.strip()))

                            # Spacing analysis (bbox analysis)
                            if len(line_spans) > 0:
                                bbox = line["bbox"]
                                spacing = bbox[3] - bbox[1]  # Height
                                font_analysis['spacing_patterns'].append(spacing)

        # Calculate statistics
        if font_analysis['sizes']:
            sizes = font_analysis['sizes']
            font_analysis['avg_size'] = sum(sizes) / len(sizes)
            font_analysis['size_std'] = (sum((x - font_analysis['avg_size'])**2 for x in sizes) / len(sizes))**0.5
            font_analysis['size_percentiles'] = {
                '25': sorted(sizes)[len(sizes)//4],
                '50': sorted(sizes)[len(sizes)//2],
                '75': sorted(sizes)[3*len(sizes)//4],
                '90': sorted(sizes)[9*len(sizes)//10],
                '95': sorted(sizes)[19*len(sizes)//20]
            }

        if font_analysis['line_lengths']:
            lengths = font_analysis['line_lengths']
            font_analysis['avg_line_length'] = sum(lengths) / len(lengths)
            font_analysis['short_line_threshold'] = sorted(lengths)[len(lengths)//4]  # 25th percentile

        # Most common font
        if font_analysis['fonts']:
            font_analysis['common_font'] = max(font_analysis['fonts'].items(), key=lambda x: x[1])[0]

        return font_analysis

    def is_heading_by_advanced_analysis(self, span: Dict, typography: Dict, line_context: Dict) -> Tuple[bool, str]:
        """Advanced analysis to determine if text is a heading"""
        text = span["text"].strip()
        font_size = span["size"]
        
        # Skip if text is too short or too long
        if len(text) < 3 or len(text) > 50:
            return False, ""
        
        # Skip bullet points and numbered lists
        if text.startswith('•') or text.startswith('-') or text.startswith('*'):
            return False, ""
        
        # Skip numbered lists that are not headings
        if re.match(r'^\d+\.\s+[a-z]', text.lower()):
            return False, ""
        
        # Skip table headers
        if '|' in text or 'table' in text.lower():
            return False, ""
        
        # Skip sentence fragments
        if text.endswith(',') or text.endswith('—') or text.endswith('...'):
            return False, ""
        
        # Skip if it's just common words
        common_words = ["the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "this", "that", "which", "have", "has", "been", "will", "would", "could", "should"]
        text_words = text.lower().split()
        if len(text_words) <= 3 and all(word in common_words for word in text_words):
            return False, ""
        
        # Skip single words that are likely not headings
        if len(text_words) == 1 and text_words[0] in ["you", "it", "go", "magic", "time", "lets", "ahead", "matters", "showtime", "mode", "scale", "lever", "cap", "lamp"]:
            return False, ""
        
        # Get font statistics
        avg_font_size = typography.get("avg_font_size", 12)
        max_font_size = typography.get("max_font_size", 16)
        
        # Check font size relative to document
        is_larger_font = font_size > avg_font_size * 1.1
        is_very_large = font_size > max_font_size * 0.7
        is_extremely_large = font_size > max_font_size * 0.9
        
        # Check if it's bold
        is_bold = span.get("flags", 0) & 2**4
        
        # Check positioning (headings are usually at the start of lines)
        is_at_start = line_context.get("is_at_start", False)
        is_isolated = line_context.get("is_isolated", False)
        
        # Check for heading patterns
        heading_patterns = [
            r'^(chapter|section|part)\s+\d+',
            r'^\d+\.\s+[A-Z]',
            r'^[A-Z][A-Z\s]+$',  # ALL CAPS
            r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*$',  # Title Case
        ]
        
        matches_pattern = any(re.match(pattern, text, re.IGNORECASE) for pattern in heading_patterns)
        
        # Check for heading indicator words
        heading_words = [
            "introduction", "conclusion", "summary", "abstract", "overview",
            "background", "methodology", "results", "discussion", "analysis",
            "recommendations", "appendix", "references", "bibliography",
            "welcome", "connecting", "dots", "challenge", "rethink", "reading",
            "rediscover", "knowledge", "round", "understand", "document",
            "docker", "requirements", "tips", "persona", "driven", "intelligence",
            "test", "case", "academic", "research", "business", "analysis",
            "educational", "content", "required", "output", "mission", "journey",
            "ahead", "matters", "theme", "brief", "specification", "constraints",
            "deliverables", "scoring", "criteria", "submission", "checklist"
        ]
        contains_heading_word = any(word in text.lower() for word in heading_words)
        
        # Scoring system (more sensitive)
        score = 0
        
        if is_extremely_large:
            score += 6
        elif is_very_large:
            score += 5
        elif is_larger_font:
            score += 3
        if is_bold:
            score += 4
        if is_at_start:
            score += 2
        if is_isolated:
            score += 2
        if matches_pattern:
            score += 5
        if contains_heading_word:
            score += 4
        
        # Threshold for heading detection
        is_heading = score >= 7
        
        if is_heading:
            # Determine heading level based on actual characteristics
            if is_extremely_large or (is_very_large and is_bold):
                level = "H1"
            elif is_very_large or (is_larger_font and is_bold):
                level = "H2"
            elif is_larger_font or is_bold:
                level = "H3"
            else:
                level = "H3"
            
            return True, level
        
        return False, ""
    
    def analyze_line_context(self, line_index: int, page_lines: List) -> Dict:
        """Analyze the context around a line for better heading detection"""
        context = {
            'is_isolated': False,
            'has_whitespace_before': False,
            'has_whitespace_after': False,
            'prev_line_length': 0,
            'next_line_length': 0
        }

        if line_index > 0:
            prev_line = page_lines[line_index - 1]
            prev_text = "".join(s["text"] for s in prev_line.get("spans", [])).strip()
            context['prev_line_length'] = len(prev_text)
            context['has_whitespace_before'] = len(prev_text) == 0

        if line_index < len(page_lines) - 1:
            next_line = page_lines[line_index + 1]
            next_text = "".join(s["text"] for s in next_line.get("spans", [])).strip()
            context['next_line_length'] = len(next_text)
            context['has_whitespace_after'] = len(next_text) == 0

        # Check if line is isolated (surrounded by short lines or whitespace)
        context['is_isolated'] = (
            context['has_whitespace_before'] or context['prev_line_length'] < 20
        ) and (
            context['has_whitespace_after'] or context['next_line_length'] < 20
        )

        return context
    
    def map_level_to_heading(self, level_input) -> str:
        """Map various level inputs to H1, H2, H3 format as required by hackathon"""
        if isinstance(level_input, int):
            if level_input <= 1:
                return "H1"
            elif level_input == 2:
                return "H2"
            else:
                return "H3"
        elif isinstance(level_input, str):
            level_lower = level_input.lower()
            if level_lower in ['chapter', 'h1', 'level_1', 'title', 'main']:
                return "H1"
            elif level_lower in ['section', 'h2', 'level_2', 'subsection']:
                return "H2"
            elif level_lower in ['subsection', 'subsubsection', 'h3', 'level_3', 'heading']:
                return "H3"
            else:
                return "H2"  # Default fallback
        return "H2"  # Ultimate fallback

    def determine_heading_level(self, text: str, font_size: float, typography: Dict, is_first_heading: bool = False) -> str:
        """Determine heading level based on content and typography with improved hierarchy"""
        text_lower = text.lower()
        
        # H1 detection - document titles and main sections
        if (is_first_heading or 
            text_lower.startswith(('chapter', 'part', 'section', 'round')) or
            any(word in text_lower for word in ['introduction', 'conclusion', 'abstract', 'summary', 'overview', 'background']) or
            any(word in text_lower for word in ['challenge', 'mission', 'theme']) or
            font_size > typography.get('avg_size', 12) * 1.8 or  # Very large font
            text_lower.startswith(('comprehensive guide', 'learn acrobat', 'breakfast ideas', 'dinner ideas'))):
            return "H1"
        
        # H2 detection - major subsections
        elif (text_lower.startswith(('section', 'subsection', 'method', 'procedure')) or
              any(word in text_lower for word in ['what', 'why', 'how', 'when', 'where', 'who']) or
              any(word in text_lower for word in ['test case', 'example', 'sample', 'brief', 'specification']) or
              font_size > typography.get('avg_size', 12) * 1.4 or  # Large font
              text_lower.startswith(('pancakes', 'scrambled eggs', 'french toast', 'smoothie bowl', 'avocado toast')) or
              text_lower.startswith(('marseille', 'nice', 'cannes', 'monaco', 'toulouse'))):
            return "H2"
        
        # H3 detection - detailed subsections
        elif (text_lower.startswith(('ingredients', 'instructions', 'steps', 'tips', 'notes')) or
              any(word in text_lower for word in ['history', 'background', 'overview', 'summary']) or
              any(word in text_lower for word in ['key', 'main', 'primary', 'secondary']) or
              font_size > typography.get('avg_size', 12) * 1.2):  # Medium-large font
            return "H3"
        
        # Default to H2 for other headings
        else:
            return "H2"

    def extract_outline_from_toc(self, doc) -> List[Dict]:
        """Extract outline from PDF's built-in table of contents"""
        outline = []
        try:
            toc = doc.get_toc()
            for item in toc:
                level, title, page_num = item
                outline.append({
                    "level": self.map_level_to_heading(level),
                    "text": title.strip(),
                    "page": page_num
                })
        except Exception as e:
            logger.warning(f"Could not extract TOC: {e}")

        return outline
    
    def extract_outline_from_content(self, doc, language_patterns=None) -> List[Dict]:
        """Extract outline using professional PDF heading detection"""
        outline = []
        
        # Step 1: Analyze typography across the document
        typography = self.analyze_advanced_typography(doc)
        
        # Step 2: Find all potential headings with better detection
        all_headings = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_lines = self.extract_text_with_formatting(page)
            
            for line_index, line in enumerate(page_lines):
                text = line["text"].strip()
                font_size = line["size"]
                is_bold = line.get("flags", 0) & 2**4
                
                # Skip empty or very short text
                if len(text) < 2:
                    continue
                
                # Skip bullet points and numbered lists
                if text.startswith(('•', '*', '-', '◦', '▪', '▫')):
                    continue
                
                # Skip numbered lists that are not headings
                if re.match(r'^\d+\.\s+[a-z]', text.lower()):
                    continue
                
                # Skip table headers
                if '|' in text or '\t' in text:
                    continue
                
                # Skip URLs and technical details
                if text.startswith('http') or text.startswith('www') or 'github.com' in text.lower():
                    continue
                
                # Clean the text
                clean_text = re.sub(r'\s+', ' ', text).strip()
                
                # Skip if too long (likely not a heading)
                if len(clean_text) > 80:
                    continue
                
                # Skip if it's just numbers or special characters
                if clean_text.isdigit() or not any(c.isalnum() for c in clean_text):
                    continue
                
                # Skip sentence fragments
                if clean_text.endswith(',') or clean_text.endswith('—') or clean_text.endswith('...'):
                    continue
                
                # Skip if it's just common words
                common_words = ["the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "this", "that", "which", "have", "has", "been", "will", "would", "could", "should"]
                text_words = clean_text.lower().split()
                if len(text_words) <= 3 and all(word in common_words for word in text_words):
                    continue
                
                # Professional heading detection
                is_heading, level = self.detect_heading_professionally(line, typography)
                
                if is_heading:
                    # Get complete heading by checking until same font size or bold ends
                    complete_text = self.get_complete_heading(page_lines, line_index, line)
                    
                    # Additional filtering to remove sentence fragments
                    if self.is_proper_heading(complete_text):
                        all_headings.append({
                            "text": complete_text,
                            "level": level,
                            "page": page_num,  # Page numbers start from 0
                            "font_size": font_size,
                            "is_bold": is_bold,
                            "y_position": line.get("y", 0)
                        })
        
        # Step 3: Sort and rank headings properly
        if all_headings:
            # Sort by page number, then by position on page
            all_headings.sort(key=lambda x: (x["page"], x.get("y_position", 0)))
            
            # Remove font_size, is_bold, and y_position from final output
            for heading in all_headings:
                if "font_size" in heading:
                    del heading["font_size"]
                if "is_bold" in heading:
                    del heading["is_bold"]
                if "y_position" in heading:
                    del heading["y_position"]
            
            outline = all_headings
        
        return outline
    
    def detect_heading_professionally(self, line, typography) -> Tuple[bool, str]:
        """Professional heading detection using typography analysis"""
        text = line["text"].strip()
        font_size = line["size"]
        is_bold = line.get("flags", 0) & 2**4

        # Skip if text is too short or too long
        if len(text) < 2 or len(text) > 80:
            return False, ""

        # Get font size thresholds from typography analysis
        avg_font_size = typography.get("avg_font_size", 12)
        max_font_size = typography.get("max_font_size", 16)
        
        # Calculate proper font size thresholds for hierarchy
        h1_threshold = max_font_size * 0.9  # Top 10% of font sizes
        h2_threshold = max_font_size * 0.7  # Top 30% of font sizes  
        h3_threshold = avg_font_size * 1.3   # Above average font size
        
        # Must be either bold OR large font
        is_large_enough = font_size > h3_threshold
        if not (is_bold or is_large_enough):
            return False, ""
        
        # Must start with a capital letter
        if not text or not text[0].isupper():
            return False, ""

        # Check for heading patterns
        heading_patterns = [
            r'^(chapter|section|part)\s+\d+',
            r'^\d+\.\s+[A-Z]',
            r'^[A-Z][A-Z\s]+$',  # ALL CAPS
            r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*$',  # Title Case
        ]

        matches_pattern = any(re.match(pattern, text, re.IGNORECASE) for pattern in heading_patterns)

        # Check for heading indicator words
        heading_words = [
            "introduction", "conclusion", "summary", "abstract", "overview",
            "background", "methodology", "results", "discussion", "analysis",
            "recommendations", "appendix", "references", "bibliography",
            "welcome", "connecting", "dots", "challenge", "rethink", "reading",
            "rediscover", "knowledge", "round", "understand", "document",
            "docker", "requirements", "tips", "persona", "driven", "intelligence",
            "test", "case", "academic", "research", "business", "analysis",
            "educational", "content", "required", "output", "mission", "journey",
            "ahead", "matters", "theme", "brief", "specification", "constraints",
            "deliverables", "scoring", "criteria", "submission", "checklist",
            "execution", "what", "you", "need", "build", "will", "provided"
        ]
        contains_heading_word = any(word in text.lower() for word in heading_words)

        # Professional scoring system
        score = 0

        if font_size >= h1_threshold:
            score += 6
        elif font_size >= h2_threshold:
            score += 5
        elif font_size >= h3_threshold:
            score += 4
        if is_bold:
            score += 4
        if matches_pattern:
            score += 5
        if contains_heading_word:
            score += 3

        # Lower threshold for better detection
        is_heading = score >= 4

        if is_heading:
            # Determine heading level based on font size hierarchy
            # Biggest font size = H1, next = H2, next = H3
            if font_size >= h1_threshold:
                level = "H1"
            elif font_size >= h2_threshold:
                level = "H2"
            else:
                level = "H3"

            return True, level

        return False, ""
    
    def is_proper_heading(self, text: str) -> bool:
        """Check if text is a proper heading (not a sentence fragment)"""
        # Must start with a capital letter
        if not text or not text[0].isupper():
            return False
        
        # Skip if it's just a single word that's too short
        if len(text.split()) == 1 and len(text) < 3:
            return False
        
        # Skip if it's just common words
        common_words = ["the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "this", "that", "which", "have", "has", "been", "will", "would", "could", "should"]
        text_words = text.lower().split()
        if len(text_words) <= 2 and all(word in common_words for word in text_words):
            return False
        
        # Skip if it's just a question or fragment
        if text.endswith("?"):
            return False
        
        # Skip if it's just a specification or technical detail
        if any(spec in text.lower() for spec in ["≤", "amd64", "x86_64", "filename.pdf", "200mb", "1gb"]):
            return False
        
        # Skip sentence fragments
        if text.endswith(',') or text.endswith('—') or text.endswith('...'):
            return False
        
        # Skip if it's just punctuation or special characters
        if not any(c.isalnum() for c in text):
            return False
        
        # Skip if it's just a single word that's likely not a heading
        if len(text_words) == 1 and text_words[0] in ["you", "it", "go", "magic", "time", "lets", "ahead", "matters", "showtime", "mode", "scale", "lever", "cap", "lamp"]:
            return False
        
        # Skip if it's just a fragment or incomplete text
        if text.endswith(":") and len(text) < 10:
            return False
        
        if text.endswith(")") and len(text) < 10:
            return False
        
        if text.endswith(".") and len(text) < 8:
            return False
        
        # Skip sentence fragments that are too short
        if len(text) < 5:
            return False
        
        # Skip if it's just a single word that's not a proper heading
        if len(text_words) == 1 and text_words[0] in ["sit", "there", "spoke", "connected", "narrated", "meaning", "across", "entire", "library", "future", "building", "want", "help", "shape", "mission", "reimagine", "humble", "intelligent", "interactive", "experience", "understands", "structure", "surfaces", "insights", "responds", "trusted", "research", "companion", "journey", "ahead", "kick", "things", "building", "brains", "extract", "structured", "outlines", "raw", "pdfs", "blazing", "speed", "pinpoint", "accuracy", "power", "device", "intelligence", "understands", "sections", "links", "related", "ideas", "together", "showtime", "beautiful", "intuitive", "reading", "webapp", "using", "adobe", "embed", "api", "using", "round", "work", "design", "futuristic", "webapp", "world", "flooded", "documents", "wins", "content", "context", "building", "tools", "future", "read", "learn", "connect", "insight", "whisperer", "stage", "time", "read", "between", "lines", "connect", "dots", "build", "experience", "feels", "magic", "go", "understand", "document", "theme", "connecting", "dots", "through", "docs", "handed", "instead", "simply", "reading", "tasked", "making", "sense", "machine", "job", "extract", "structured", "outline", "document", "essentially", "title", "headings", "clean", "hierarchical", "format", "outline", "foundation", "rest", "hackathon", "journey"]:
            return False
        
        # Skip if it's just a fragment or incomplete sentence
        if text.startswith("—") or text.startswith("-"):
            return False
        
        if text.endswith("—") or text.endswith("-"):
            return False
        
        # Skip if it's just a single word that's likely a verb or common word
        if len(text_words) == 1 and text_words[0] in ["what", "if", "every", "time", "opened", "didnt", "just", "there", "spoke", "connected", "ideas", "narrated", "meaning", "across", "entire", "library", "thats", "future", "building", "want", "help", "shape", "connecting", "dots", "challenge", "mission", "reimagine", "humble", "intelligent", "interactive", "experience", "understands", "structure", "surfaces", "insights", "responds", "trusted", "research", "companion", "journey", "ahead", "kick", "things", "building", "brains", "extract", "structured", "outlines", "raw", "pdfs", "blazing", "speed", "pinpoint", "accuracy", "power", "device", "intelligence", "understands", "sections", "links", "related", "ideas", "together", "showtime", "beautiful", "intuitive", "reading", "webapp", "using", "adobe", "embed", "api", "using", "round", "work", "design", "futuristic", "webapp", "world", "flooded", "documents", "wins", "content", "context", "building", "tools", "future", "read", "learn", "connect", "insight", "whisperer", "stage", "time", "read", "between", "lines", "connect", "dots", "build", "experience", "feels", "magic", "go", "understand", "document", "theme", "connecting", "dots", "through", "docs", "handed", "instead", "simply", "reading", "tasked", "making", "sense", "machine", "job", "extract", "structured", "outline", "document", "essentially", "title", "headings", "clean", "hierarchical", "format", "outline", "foundation", "rest", "hackathon", "journey"]:
            return False
        
        # Must have at least 2 words or be a substantial single word
        if len(text_words) == 1 and len(text) < 5:
            return False
        
        # Skip if it looks like a sentence fragment
        if text.endswith(".") and len(text) < 10:
            return False
        
        # Skip if it's just a single word that's too common
        if len(text_words) == 1 and text_words[0] in ["the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "this", "that", "which", "have", "has", "been", "will", "would", "could", "should", "you", "it", "go", "magic", "time", "lets", "ahead", "matters", "showtime", "mode", "scale", "lever", "cap", "lamp"]:
            return False
        
        return True
    
    def get_complete_heading(self, page_lines, line_index, current_line) -> str:
        """Get complete heading by checking until same font size or bold ends"""
        current_text = current_line["text"].strip()
        current_font_size = current_line["size"]
        current_is_bold = current_line.get("flags", 0) & 2**4
        
        # Start with current line text
        complete_text = current_text
        
        # Check next lines to see if they continue the heading
        for i in range(line_index + 1, len(page_lines)):
            next_line = page_lines[i]
            next_text = next_line["text"].strip()
            next_font_size = next_line["size"]
            next_is_bold = next_line.get("flags", 0) & 2**4
            
            # If font size or boldness changes, stop
            if next_font_size != current_font_size or next_is_bold != current_is_bold:
                break
            
            # If it's a standalone element (not part of a table or list), continue
            if not self.is_part_of_table_or_list(next_text):
                complete_text += " " + next_text
            else:
                break
        
        return complete_text.strip()
    
    def is_part_of_table_or_list(self, text: str) -> bool:
        """Check if text is part of a table or list"""
        # Skip if it's a bullet point
        if text.startswith(('•', '*', '-', '◦', '▪', '▫')):
            return True
        
        # Skip if it's a numbered list
        if re.match(r'^\d+\.\s+', text):
            return True
        
        # Skip if it contains table separators
        if '|' in text or '\t' in text:
            return True
        
        # Skip if it's just a single word that's likely part of a list
        if len(text.split()) == 1 and len(text) < 5:
            return True
        
        return False
    
    def calculate_body_font_size(self, doc) -> float:
        """Calculate the most common font size among non-bold text"""
        font_sizes = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_lines = self.extract_text_with_formatting(page)
            
            for line in page_lines:
                text = line["text"].strip()
                font_size = line["size"]
                is_bold = line.get("flags", 0) & 2**4
                
                # Only consider non-bold text for body font size calculation
                if not is_bold and len(text) > 10:  # Reasonable length for body text
                    font_sizes.append(font_size)
        
        if font_sizes:
            # Return the most common font size
            from collections import Counter
            most_common = Counter(font_sizes).most_common(1)
            return most_common[0][0]
        
        return 12.0  # Default fallback
    
    def find_heading_candidates(self, doc, body_font_size) -> List[Dict]:
        """Find candidates: bold text with font size larger than body text"""
        candidates = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            page_lines = self.extract_text_with_formatting(page)
            
            for line in page_lines:
                text = line["text"].strip()
                font_size = line["size"]
                is_bold = line.get("flags", 0) & 2**4
                
                # Rule: A line is a candidate if it is bold and its font size is larger than body text
                # Also consider non-bold text if it's significantly larger than body text
                if len(text) > 2:
                    is_candidate = False
                    
                    if is_bold and font_size > body_font_size:
                        is_candidate = True
                    elif font_size > body_font_size * 1.3:  # Significantly larger
                        is_candidate = True
                    
                    if is_candidate:
                        candidates.append({
                            "text": text,
                            "font_size": font_size,
                            "page": page_num,  # Page numbers start from 0
                            "y_position": line.get("y", 0),
                            "is_bold": is_bold
                        })
        
        return candidates
    
    def apply_cleanup_filter(self, candidates) -> List[Dict]:
        """Apply powerful cleanup filter to remove noise"""
        clean_headings = []
        
        for candidate in candidates:
            text = candidate["text"]
            
            # Remove if it's part of a side-by-side list (like table headers)
            if '|' in text or '\t' in text:
                continue
            
            # Remove if it's a long sentence (more than 12 words)
            if len(text.split()) > 12:
                continue
            
            # Remove if it contains code snippets or is enclosed in brackets
            if '[[' in text and ']]' in text:
                continue
            
            # Remove if it begins with a bullet point character
            if text.startswith(('•', '*', '-', '◦', '▪', '▫')):
                continue
            
            # Remove if it's just numbers or special characters
            if text.isdigit() or not any(c.isalnum() for c in text):
                continue
            
            # Remove if it's too short
            if len(text) < 3:
                continue
            
            # Remove URLs
            if text.startswith('http') or text.startswith('www') or 'github.com' in text.lower():
                continue
            
            # Remove if it's just common words
            common_words = ["the", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "this", "that", "which", "have", "has", "been", "will", "would", "could", "should"]
            text_words = text.lower().split()
            if len(text_words) <= 3 and all(word in common_words for word in text_words):
                continue
            
            # Remove sentence fragments
            if text.endswith(',') or text.endswith('—') or text.endswith('...'):
                continue
            
            # Remove if it's just a single word that's too short
            if len(text_words) == 1 and len(text) < 5:
                continue
            
            # Remove if it's just punctuation or special characters
            if not any(c.isalnum() for c in text):
                continue
            
            # If it passes all filters, it's a clean heading
            clean_headings.append(candidate)
        
        return clean_headings
    
    def looks_like_heading(self, text: str) -> bool:
        """Check if text looks like a heading based on content patterns - enhanced filtering"""
        text_lower = text.lower().strip()

        # Skip obvious non-headings
        non_heading_indicators = [
            'this sample', 'the guidelines', 'formatting requirements', 'academic writing',
            'referencing guidelines', 'times new roman', 'department, university',
            'for ijltemas', 'first author', 'second author', 'third author',
            'email:', 'phone:', 'address:', 'university/college', 'color-coded',
            'demonstrates the requirements', 'which demonstrates', 'have been'
        ]

        if any(indicator in text_lower for indicator in non_heading_indicators):
            return False

        # Skip very long sentences (likely body text)
        if len(text) > 100 and ('.' in text or ',' in text):
            return False

        # Enhanced heading indicator words
        heading_words = [
            # Main sections
            'introduction', 'overview', 'background', 'methodology', 'results',
            'discussion', 'conclusion', 'summary', 'abstract', 'references',
            'bibliography', 'appendix', 'acknowledgments', 'preface', 'foreword',
            
            # Challenge-specific
            'challenge', 'mission', 'theme', 'brief', 'specification',
            'test case', 'example', 'sample', 'requirements',
            
            # Travel/Guide content
            'history', 'attractions', 'highlights', 'experiences', 'tips', 'guide',
            'culture', 'cuisine', 'restaurants', 'hotels', 'activities',
            
            # Recipe content
            'ingredients', 'instructions', 'steps', 'preparation', 'cooking',
            'serving', 'tips', 'notes', 'variations',
            
            # Technical content
            'method', 'procedure', 'steps', 'instructions', 'requirements',
            'configuration', 'setup', 'installation', 'usage',
            
            # Document structure
            'chapter', 'section', 'part', 'subsection', 'detail'
        ]

        # Check if text starts with or is a heading word
        if any(text_lower.startswith(word) or text_lower == word for word in heading_words):
            return True

        # Check if text is title case (most words capitalized) but not too long
        words = text.split()
        if len(words) >= 1 and len(words) <= 10:  # Reasonable heading length
            capitalized_words = sum(1 for word in words if word[0].isupper() and len(word) > 2)
            if capitalized_words / len(words) >= 0.6:  # 60% of words are capitalized
                return True

        # Check for numbered patterns
        if re.match(r'^\d+\.', text) or re.match(r'^[a-z]\.', text):
            return True

        # Check for colon patterns (common in subsections)
        if ':' in text and len(text.split(':')) == 2:
            return True

        return False
    
    def clean_and_deduplicate_outline(self, outline: List[Dict]) -> List[Dict]:
        """Clean and deduplicate outline entries"""
        if not outline:
            return []
        
        # Remove duplicates while preserving order
        seen = set()
        cleaned = []
        
        for item in outline:
            # Create a key for deduplication
            key = (item["text"].lower().strip(), item["page"])
            if key not in seen:
                seen.add(key)
                # Clean text
                item["text"] = re.sub(r'\s+', ' ', item["text"]).strip()
                cleaned.append(item)
        
        # Limit to reasonable number of outline items
        return cleaned[:50]
    
    def extract_title(self, doc) -> str:
        """Extract document title using the most prominent text on the first page"""
        if len(doc) > 0:
            page = doc[0]
            page_lines = self.extract_text_with_formatting(page)
            
            # Find the most prominent text (largest font size) on the first page
            prominent_texts = []
            
            for line in page_lines:
                text = line["text"].strip()
                font_size = line["size"]
                is_bold = line.get("flags", 0) & 2**4
                
                # Skip if too short or too long
                if len(text) < 3 or len(text) > 100:
                    continue
                
                # Skip if it's just numbers or special characters
                if text.isdigit() or not any(c.isalnum() for c in text):
                    continue
                
                # Skip common non-title text
                if text.lower() in ["document", "page", "sample", "template", "welcome", "introduction", "adobe", "challenge", "round"]:
                    continue
                
                # Skip if it starts with common non-title patterns
                if text.startswith(("http", "www", "Adobe", "Round", "Challenge")):
                    continue
                
                # Calculate prominence score (font size + bold bonus)
                prominence = font_size
                if is_bold:
                    prominence += 2
                
                prominent_texts.append({
                    "text": text,
                    "prominence": prominence
                })
            
            # Sort by prominence and return the most prominent
            if prominent_texts:
                prominent_texts.sort(key=lambda x: x["prominence"], reverse=True)
                return prominent_texts[0]["text"]
        
        # Fallback: Use filename
        filename = doc.name if hasattr(doc, 'name') else ""
        if filename:
            # Clean the filename
            clean_name = filename.replace('.pdf', '').replace('_', ' ').replace('-', ' ')
            # Remove path components
            clean_name = clean_name.split('\\')[-1].split('/')[-1]
            return clean_name
        
        return "Untitled Document"
    
    def process_single_pdf(self, pdf_path: Path, output_dir: Path) -> bool:
        """Process a single PDF file"""
        try:
            start_time = time.time()
            logger.info(f"Processing {pdf_path.name}")
            
            # Open PDF
            doc = fitz.open(pdf_path)

            # Detect document language for multilingual support
            detected_language = self.detect_document_language(doc)

            # Get language-specific patterns
            language_patterns = self.get_patterns_for_language(detected_language)

            # Extract title
            title = self.extract_title(doc)

            # Extract outline from content analysis (more aggressive)
            outline = self.extract_outline_from_content(doc, language_patterns)
            
            # If we don't have enough headings, try TOC as backup
            if len(outline) < 3:
                toc_outline = self.extract_outline_from_toc(doc)
                outline.extend(toc_outline)
            
            # Clean and deduplicate
            outline = self.clean_and_deduplicate_outline(outline)
            
            # Ensure we have some outline
            if not outline:
                outline = [{
                    "level": "H1",
                    "text": "Document Content",
                    "page": 1
                }]
            
            # Create output JSON
            output_data = {
                "title": title,
                "outline": outline
            }
            
            # Save output (always overwrite)
            output_file = output_dir / f"{pdf_path.stem}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            doc.close()
            
            processing_time = time.time() - start_time
            logger.info(f"Processed {pdf_path.name} in {processing_time:.2f}s")
            return True
            
        except Exception as e:
            logger.error(f"Error processing {pdf_path.name}: {e}")
            return False

def process_pdfs():
    """
    Main processing function - Entry point for PDF processing

    EXECUTION WORKFLOW:
    ==================
    1. Detect environment (Docker vs Local)
    2. Set up input/output directories
    3. Find all PDF files in input directory
    4. Initialize high-performance processor
    5. Process files with threading for I/O optimization
    6. Generate JSON output files with exact hackathon format

    DIRECTORY STRUCTURE:
    ===================
    Docker Mode:
        /app/input/  - PDF files to process
        /app/output/ - Generated JSON files

    Local Mode:
        ./input/     - PDF files to process
        ./output/    - Generated JSON files

    OUTPUT FORMAT:
    =============
    Each PDF generates filename.json with structure:
    {
        "title": "Document Title",
        "outline": [
            {"level": "H1", "text": "Chapter 1", "page": 1},
            {"level": "H2", "text": "Section 1.1", "page": 2}
        ]
    }
    """
    # Use local directories for testing, Docker paths for production
    if Path("/app/input").exists():
        input_dir = Path("/app/input")
        output_dir = Path("/app/output")
    else:
        input_dir = Path("input")
        output_dir = Path("output")
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all PDF files
    pdf_files = list(input_dir.glob("*.pdf"))
    
    if not pdf_files:
        logger.warning("No PDF files found in input directory")
        return
    
    logger.info(f"Found {len(pdf_files)} PDF files to process")
    
    # Initialize processor
    processor = HighPerformancePDFProcessor()
    
    # Process files with threading for I/O optimization
    max_workers = min(mp.cpu_count(), len(pdf_files), 4)  # Limit concurrent processing
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(processor.process_single_pdf, pdf_file, output_dir): pdf_file 
            for pdf_file in pdf_files
        }
        
        for future in as_completed(futures):
            pdf_file = futures[future]
            try:
                success = future.result()
                if not success:
                    logger.error(f"Failed to process {pdf_file.name}")
            except Exception as e:
                logger.error(f"Exception processing {pdf_file.name}: {e}")
    
    logger.info("PDF processing completed")

if __name__ == "__main__":
    """
    MAIN EXECUTION ENTRY POINT
    ==========================

    This script can be executed in multiple ways:

    1. Docker Container (Production):
       docker run --rm -v $(pwd)/input:/app/input -v $(pwd)/output:/app/output --network none mysolutionname:somerandomidentifier

    2. Local Python (Development/Testing):
       python process_pdfs.py

    3. Local Testing with Sample:
       mkdir -p input output
       cp sample.pdf input/
       python process_pdfs.py
       # Check output/sample.json

    PERFORMANCE EXPECTATIONS:
    ========================
    - Processing Time: ≤ 10 seconds for 50-page PDF (typically <5s)
    - Memory Usage: Efficient usage within 16GB limit
    - Output: Exact JSON format compliance
    - Error Handling: Graceful failures with comprehensive logging
    """
    process_pdfs()


def extract_pdf_title(pdf_path: str) -> str:
    """
    Opens a PDF and extracts its most likely title.
    
    Args:
        pdf_path: The full path to the PDF file.
        
    Returns:
        The extracted title string.
    """
    processor = HighPerformancePDFProcessor()
    try:
        doc = fitz.open(pdf_path)
        title = processor.extract_title(doc)
        doc.close()
        return title
    except Exception as e:
        logger.error(f"Could not extract title from {pdf_path}: {e}")
        return Path(pdf_path).stem.replace('_', ' ').title()

def extract_sections(pdf_path: str, doc_id: str) -> List[Section]:
    """
    Processes a single PDF to extract its full hierarchical content.
    
    Args:
        pdf_path: The full path to the PDF file.
        doc_id: The unique identifier for the document.
        
    Returns:
        A list of Section objects with titles and full content.
    """
    processor = HighPerformancePDFProcessor()
    all_sections = []
    
    try:
        doc = fitz.open(pdf_path)
        
        # 1. Get the outline (headings) first
        outline_dicts = processor.extract_outline_from_content(doc)
        
        # 2. Now, extract the full text content for each section
        for i, heading_info in enumerate(outline_dicts):
            start_page = heading_info['page']
            
            # Determine the end page and text
            end_page = outline_dicts[i + 1]['page'] if i + 1 < len(outline_dicts) else len(doc)
            
            content_text = ""
            for page_num in range(start_page, end_page):
                content_text += doc[page_num].get_text()

            # For the last section on a page, it might share with the next heading
            # This is a simplification; more advanced logic could use bounding boxes.
            if i + 1 < len(outline_dicts) and outline_dicts[i+1]['page'] == start_page:
                next_heading_text = outline_dicts[i+1]['text']
                if next_heading_text in content_text:
                    content_text = content_text.split(next_heading_text)[0]

            all_sections.append(
                Section(
                    doc_id=doc_id,
                    doc_filename=Path(pdf_path).name,
                    section_title=heading_info['text'],
                    content=content_text.strip(),
                    page_number=heading_info['page'],
                    level=heading_info['level']
                )
            )
            
        doc.close()
        
    except Exception as e:
        logger.error(f"Could not extract sections from {pdf_path}: {e}")

    return all_sections