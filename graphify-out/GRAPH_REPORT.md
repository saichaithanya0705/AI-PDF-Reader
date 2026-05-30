# Graph Report - backend/app + frontend/src  (2026-05-17)

## Corpus Check
- 68 files · ~79,104 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1004 nodes · 1379 edges · 31 communities detected
- Extraction: 92% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 106 edges (avg confidence: 0.67)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 8|Community 8]]
- [[_COMMUNITY_Community 9|Community 9]]
- [[_COMMUNITY_Community 10|Community 10]]
- [[_COMMUNITY_Community 11|Community 11]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]
- [[_COMMUNITY_Community 16|Community 16]]
- [[_COMMUNITY_Community 17|Community 17]]
- [[_COMMUNITY_Community 18|Community 18]]
- [[_COMMUNITY_Community 19|Community 19]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 39|Community 39]]

## God Nodes (most connected - your core abstractions)
1. `IntelligentPDFBrain` - 39 edges
2. `HighPerformancePDFProcessor` - 34 edges
3. `DocumentDatabase` - 22 edges
4. `SupabaseDatabase` - 18 edges
5. `SectionHighlighter` - 14 edges
6. `apiRequest()` - 14 edges
7. `PDFValidator` - 14 edges
8. `EnhancedLLMService` - 13 edges
9. `RAGService` - 13 edges
10. `SmartUploadHandler` - 13 edges

## Surprising Connections (you probably didn't know these)
- `chat_endpoint()` --calls--> `get_chat_history_manager()`  [INFERRED]
  backend\app\main.py → backend\app\chat_history.py
- `DuplicatePDFCleaner` --uses--> `DocumentDatabase`  [INFERRED]
  backend\app\duplicate_cleaner.py → backend\app\database.py
- `process_pdf()` --calls--> `HighPerformancePDFProcessor`  [INFERRED]
  backend\app\main.py → backend\app\utils\process_pdfs.py
- `process_pdf()` --calls--> `IntelligentPDFBrain`  [INFERRED]
  backend\app\main.py → backend\app\utils\intelligent_pdf_brain.py
- `get_recommendations()` --calls--> `IntelligentPDFBrain`  [INFERRED]
  backend\app\main.py → backend\app\utils\intelligent_pdf_brain.py

## Communities (44 total, 9 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.03
Nodes (75): PersonaJobSuggestionsRequest, UserIntentRequest, Document, Document model representing a PDF file in the system, Convert document to dictionary for JSON serialization, EnhancedLLMService, Enhanced LLM Service for Adobe Hackathon Uses provided chat_with_llm.py for all, Generate insights bulb content - bonus feature (+5 points) (+67 more)

### Community 1 - "Community 1"
Cohesion: 0.03
Nodes (61): create_chat_session_endpoint(), delete_chat_session_endpoint(), get_chat_session_endpoint(), list_chat_sessions_endpoint(), Create a new chat session, Get all chat sessions for current user, Get messages for a specific session, Delete a chat session (+53 more)

### Community 2 - "Community 2"
Cohesion: 0.05
Nodes (38): IntelligentPDFBrain, InteractivePDFExperience, main(), Generate insights about content connections, Generate strategic summary insights, Calculate enhanced relevance score with semantic understanding, Process collection with full intelligence capabilities, Revolutionary PDF Intelligence System (+30 more)

### Community 3 - "Community 3"
Cohesion: 0.04
Nodes (34): Database models and operations for PDF document management, DuplicatePDFCleaner, Remove duplicate PDFs, keeping the most recently used one, Main method to find and remove duplicates, Calculate SHA-256 hash of file content, Convenience function to run duplicate cleanup, Get file size in bytes, Find duplicate PDFs based on file hash and size (+26 more)

### Community 4 - "Community 4"
Cohesion: 0.04
Nodes (28): AzureOpenAIProvider, GeminiProvider, get_llm_provider(), LLMProvider, LLMResponse, OllamaProvider, OpenAIProvider, Enhanced LLM Provider for Adobe Hackathon - Integrates provided chat_with_llm.py (+20 more)

### Community 5 - "Community 5"
Cohesion: 0.05
Nodes (31): extract_pdf_title(), extract_sections(), HighPerformancePDFProcessor, process_pdfs(), Clean and deduplicate outline entries, Extract document title using the most prominent text on the first page, Process a single PDF file, Main processing function - Entry point for PDF processing      EXECUTION WORKFLO (+23 more)

### Community 6 - "Community 6"
Cohesion: 0.05
Nodes (35): ChunkingService, DocumentChunk, Document Chunking Service for RAG Splits PDF documents into smaller chunks for, Recursively split text into chunks                  Args:             text: T, Represents a chunk of a document, Service for chunking PDF documents using recursive character splitting, Initialize the chunking service                  Args:             chunk_size, Chunk a PDF document into smaller pieces                  Args:             p (+27 more)

### Community 7 - "Community 7"
Cohesion: 0.05
Nodes (43): build_enriched_messages(), build_library_context(), build_pdf_context(), get_page_content(), Context Builder Module for Context-Aware Chatbot  This module builds contextua, Build context for library page chatbot interactions          Args:         db, Build context for PDF viewer page chatbot interactions          Args:, Search across all user's documents using vector similarity          Args: (+35 more)

### Community 8 - "Community 8"
Cohesion: 0.06
Nodes (28): analyzeTextSelection(), ApiError, apiRequest(), askGPT(), deleteAllDocuments(), deleteDocument(), generateAudio(), generatePodcast() (+20 more)

### Community 9 - "Community 9"
Cohesion: 0.06
Nodes (30): EnhancedPDFSplitter, main(), PDFSplitterError, Validate PDF file and return page count.                  Args:             file, Get user input for PDF splitting parameters.                  Returns:, Generate output filename with incremental numbering if file exists., Split PDF into multiple files based on user specifications.                  Arg, Main method to process PDF splitting with user interaction. (+22 more)

### Community 10 - "Community 10"
Cohesion: 0.05
Nodes (22): DocumentDatabase, Create a new document record, Get documents with optional pagination and tenant filtering, Get a specific document by ID with optional tenant filtering, Get metadata/sections for a document, Delete a document and all its related data, Update document fields, Delete a document (soft delete by default) (+14 more)

### Community 11 - "Community 11"
Cohesion: 0.08
Nodes (25): classify_user_intent_endpoint(), get_persona_job_suggestions_endpoint(), Classify user intent into appropriate persona and job using AI/NLP          This, Get alternative persona and job suggestions based on user input          Returns, ClassificationResult, classify_user_intent(), get_persona_job_suggestions(), JobMatch (+17 more)

### Community 12 - "Community 12"
Cohesion: 0.07
Nodes (33): bulk_delete_documents(), delete_all_documents(), delete_document(), force_delete_document(), get_all_documents(), get_available_jobs(), get_available_personas(), get_document() (+25 more)

### Community 13 - "Community 13"
Cohesion: 0.07
Nodes (6): InsightsPanel(), RelatedDocumentsSidebar(), handleAskGPT(), PDFProvider(), usePDF(), ReaderPage()

### Community 14 - "Community 14"
Cohesion: 0.09
Nodes (17): ABC, AzureTTSProvider, get_tts_provider(), GoogleTTSProvider, LocalTTSProvider, Text-to-Speech Service for Adobe Hackathon Supports Azure TTS with fallback opti, Fallback TTS provider using Google TTS, Generate audio using Google TTS API (+9 more)

### Community 15 - "Community 15"
Cohesion: 0.1
Nodes (17): IPRateLimiter, rate_limit_auth(), rate_limit_default(), rate_limit_upload(), RateLimiter, Rate limiting middleware to prevent API abuse, Simple in-memory rate limiter          For production, consider using Redis fo, Get rate limit headers for response (+9 more)

### Community 16 - "Community 16"
Cohesion: 0.13
Nodes (13): PDFComparator, PDFComparisonResult, Robust PDF Comparison System High-performance PDF comparison using multiple tech, Fast hash-based comparison using SHA256, Deep binary comparison using recursive binary search approach         Optimized, Result of PDF comparison, Recursive binary search similarity calculation         Divides file into chunks, Recursive chunk comparison using binary search approach (+5 more)

### Community 17 - "Community 17"
Cohesion: 0.11
Nodes (12): ChatHistoryManager, Chat History Manager Module  Handles persistence of chat conversations to data, Save a chat message to the database                  Args:             user_i, Retrieve conversation history for a session                  Args:, Get all chat sessions for a user                  Args:             user_id:, Get a specific session by ID                  Args:             session_id: C, Delete a chat session and all its messages                  Args:, Manages chat conversation history with database persistence (+4 more)

### Community 18 - "Community 18"
Cohesion: 0.14
Nodes (9): ProtectedRoute(), handleKeyPress(), sendMessage(), resetError(), signIn(), signUp(), useAuth(), handleSubmit() (+1 more)

### Community 20 - "Community 20"
Cohesion: 0.2
Nodes (4): checkAdobeAPIAvailability(), checkOnlineStatus(), getNetworkStatus(), NetworkStatusMonitor

### Community 21 - "Community 21"
Cohesion: 0.22
Nodes (13): _chunk_text_by_chars(), generate_audio(), _generate_azure_tts(), _generate_cloud_tts_chunked(), _generate_gcp_tts(), _generate_local_tts(), Split text into chunks not exceeding max_chars, preferring whitespace boundaries, Chunk long text for cloud providers and concatenate resulting audio files. (+5 more)

### Community 25 - "Community 25"
Cohesion: 0.43
Nodes (5): getBestPDFJSConfig(), initializePDFJS(), loadPDFDocument(), loadPDFJSLibrary(), testUrlAccessibility()

## Knowledge Gaps
- **373 isolated node(s):** `API routes for document management`, `Get all documents with optional filtering and pagination`, `Get a specific document by ID`, `Delete a document (soft delete by default)`, `Update document metadata` (+368 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **9 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `IntelligentPDFBrain` connect `Community 2` to `Community 0`, `Community 7`?**
  _High betweenness centrality (0.091) - this node is a cross-community bridge._
- **Why does `HighPerformancePDFProcessor` connect `Community 5` to `Community 0`, `Community 7`?**
  _High betweenness centrality (0.088) - this node is a cross-community bridge._
- **Why does `get_chat_history_manager()` connect `Community 1` to `Community 17`, `Community 7`?**
  _High betweenness centrality (0.067) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `IntelligentPDFBrain` (e.g. with `AskGPTRequest` and `TextSelectionAnalysisRequest`) actually correct?**
  _`IntelligentPDFBrain` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Are the 5 inferred relationships involving `HighPerformancePDFProcessor` (e.g. with `AskGPTRequest` and `TextSelectionAnalysisRequest`) actually correct?**
  _`HighPerformancePDFProcessor` has 5 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `SectionHighlighter` (e.g. with `AskGPTRequest` and `TextSelectionAnalysisRequest`) actually correct?**
  _`SectionHighlighter` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `API routes for document management`, `Get all documents with optional filtering and pagination`, `Get a specific document by ID` to the rest of the system?**
  _373 weakly-connected nodes found - possible documentation gaps or missing edges._