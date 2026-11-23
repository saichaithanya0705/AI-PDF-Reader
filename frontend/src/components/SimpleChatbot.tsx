import React, { useState, useRef, useEffect } from 'react';
import {
  MessageSquare,
  Send,
  X,
  Loader2,
  Minimize2,
  History,
  FileText,
  ExternalLink,
  Copy,
  Check,
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import ChatHistory from './ChatHistory';
import { getChatSession, sendChatMessage } from '../lib/api';

interface RelatedDocument {
  id: string;
  document_id: string;
  document_name: string;
  page_number: number;
  text: string;
  similarity: number;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  relatedDocuments?: RelatedDocument[];
}

interface SimpleChatbotProps {
  documentId?: string;
  documentContext?: string;
  currentPage?: number;
  viewType?: 'library' | 'pdf_viewer';
  onClose?: () => void;
  isMinimized?: boolean;
  onToggleMinimize?: () => void;
  initialMessage?: string;
  variant?: 'floating' | 'docked';
}

const buildWelcomeMessage = (documentContext?: string): Message => ({
  role: 'assistant',
  content: documentContext
    ? 'Ask a question about this page or highlight any excerpt in the PDF to inspect it here.'
    : 'Ask a question across your document library. Answers include links to the relevant pages.',
  timestamp: new Date(),
});

const SimpleChatbot: React.FC<SimpleChatbotProps> = ({
  documentId,
  documentContext,
  currentPage,
  viewType,
  onClose,
  isMinimized = false,
  onToggleMinimize,
  initialMessage,
  variant = 'floating',
}) => {
  const navigate = useNavigate();
  const [messages, setMessages] = useState<Message[]>(() => [buildWelcomeMessage(documentContext)]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [showHistory, setShowHistory] = useState(false);
  const [selectedChatText, setSelectedChatText] = useState('');
  const [selectionMenuPosition, setSelectionMenuPosition] = useState<{ x: number; y: number } | null>(null);
  const [copiedSelection, setCopiedSelection] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (!isMinimized && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isMinimized]);

  useEffect(() => {
    if (initialMessage && !isMinimized) {
      setInputMessage(initialMessage);
      inputRef.current?.focus();
    }
  }, [initialMessage, isMinimized]);

  useEffect(() => {
    if (isMinimized) return;

    const handleChatSelection = () => {
      const selection = window.getSelection();
      const text = selection?.toString().trim();

      if (!selection || !text || text.length < 2 || selection.rangeCount === 0) {
        setSelectedChatText('');
        setSelectionMenuPosition(null);
        setCopiedSelection(false);
        return;
      }

      const range = selection.getRangeAt(0);
      const selectionNode = range.commonAncestorContainer;
      const selectionElement =
        selectionNode.nodeType === Node.ELEMENT_NODE
          ? (selectionNode as Element)
          : selectionNode.parentElement;
      const isInsideMessages = Boolean(messagesContainerRef.current?.contains(selectionNode));
      const isInteractiveChrome = Boolean(
        selectionElement?.closest('button, input, textarea, [contenteditable="true"], [data-chat-selection-ignore="true"]')
      );

      if (isInsideMessages && !isInteractiveChrome) {
        const rect = range.getBoundingClientRect();
        setSelectedChatText(text);
        setSelectionMenuPosition({
          x: rect.left + rect.width / 2,
          y: rect.top - 10,
        });
      } else {
        setSelectedChatText('');
        setSelectionMenuPosition(null);
        setCopiedSelection(false);
      }
    };

    window.document.addEventListener('mouseup', handleChatSelection);
    window.document.addEventListener('selectionchange', handleChatSelection);

    return () => {
      window.document.removeEventListener('mouseup', handleChatSelection);
      window.document.removeEventListener('selectionchange', handleChatSelection);
    };
  }, [isMinimized]);

  const clearChatSelection = () => {
    window.getSelection()?.removeAllRanges();
    setSelectedChatText('');
    setSelectionMenuPosition(null);
    setCopiedSelection(false);
  };

  const askAboutSelectedChatText = () => {
    if (!selectedChatText.trim()) return;
    setInputMessage(`Regarding this chat excerpt: "${selectedChatText}"\n\nQuestion: `);
    clearChatSelection();
    inputRef.current?.focus();
  };

  const copySelectedChatText = async () => {
    if (!selectedChatText.trim()) return;
    await navigator.clipboard.writeText(selectedChatText);
    setCopiedSelection(true);
    setTimeout(() => setCopiedSelection(false), 1500);
  };

  const normalizeRelatedDocuments = (value: unknown): RelatedDocument[] => {
    if (!Array.isArray(value)) return [];

    return value
      .filter((entry): entry is Record<string, unknown> => typeof entry === 'object' && entry !== null)
      .map((entry) => ({
        id: typeof entry.id === 'string' ? entry.id : `${entry.document_id || 'doc'}-${entry.page_number || 1}`,
        document_id: typeof entry.document_id === 'string' ? entry.document_id : '',
        document_name: typeof entry.document_name === 'string' ? entry.document_name : 'Document',
        page_number: typeof entry.page_number === 'number' ? entry.page_number : 1,
        text: typeof entry.text === 'string' ? entry.text : '',
        similarity: typeof entry.similarity === 'number' ? entry.similarity : 0,
      }))
      .filter((entry) => entry.document_id);
  };

  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return;

    const userMessage: Message = {
      role: 'user',
      content: inputMessage,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const data = await sendChatMessage({
        message: inputMessage,
        documentId,
        currentPage,
        contextType: viewType || (documentId ? 'pdf_viewer' : 'library'),
        sessionId,
        conversationHistory: messages.slice(-5).map((message) => ({
          role: message.role,
          content: message.content,
        })),
      });

      if (typeof data.session_id === 'string' && data.session_id !== sessionId) {
        setSessionId(data.session_id);
      }

      const context =
        typeof data.context === 'object' && data.context !== null
          ? (data.context as Record<string, unknown>)
          : {};
      const relatedDocs = normalizeRelatedDocuments(
        data.related_documents || data.sources || context.search_results || context.related_documents
      );

      const assistantMessage: Message = {
        role: 'assistant',
        content: data.response,
        timestamp: new Date(),
        relatedDocuments: relatedDocs,
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Chat error:', error);
      const errorMessage: Message = {
        role: 'assistant',
        content: 'Unable to reach the assistant right now. Try sending your question again.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const loadSession = async (sessionIdToLoad: string) => {
    try {
      const data = await getChatSession(sessionIdToLoad);
      const loadedMessages: Message[] = data.messages.map((message) => ({
        role: message.role,
        content: message.content,
        timestamp: new Date(message.created_at),
        relatedDocuments: normalizeRelatedDocuments(
          message.metadata?.sources || message.metadata?.search_results
        ),
      }));

      setMessages(loadedMessages.length > 0 ? loadedMessages : [buildWelcomeMessage(documentContext)]);
      setSessionId(sessionIdToLoad);
    } catch (error) {
      console.error('Error loading session:', error);
      alert('Failed to load chat session');
      throw error;
    }
  };

  const handleSessionDeleted = (deletedSessionId: string) => {
    if (deletedSessionId !== sessionId) {
      return;
    }

    setSessionId(null);
    setMessages([buildWelcomeMessage(documentContext)]);
  };

  const handleNavigateToDocument = (docId: string, page: number) => {
    navigate(`/reader/${docId}?page=${page}`);
  };

  if (isMinimized) {
    if (variant === 'docked') {
      return null;
    }

    return (
      <div className="fixed bottom-phi-5 right-phi-5 z-40">
        <button
          type="button"
          onClick={onToggleMinimize}
          className="inline-flex h-phi-ctrl items-center gap-phi-2 rounded-phi-md border border-[rgba(25,24,22,0.14)] bg-ink-primary px-phi-4 text-phi-sm font-medium text-paper-50 shadow-float transition-colors duration-phi-fast hover:bg-[#2c2a26] active:scale-[0.98]"
        >
          <MessageSquare className="h-4 w-4" strokeWidth={1.5} />
          <span>Document chat</span>
          {messages.length > 1 && (
            <span className="ml-phi-1 font-mono text-phi-xs tabular-nums text-paper-300">
              {messages.length - 1}
            </span>
          )}
        </button>
      </div>
    );
  }

  // Floating chat panel uses an exact 1 : 1.618 golden rectangle (w-phi-chat × h-phi-chat-h)
  const containerClass =
    variant === 'docked'
      ? 'flex h-full w-full flex-col overflow-hidden bg-app-surface'
      : 'fixed bottom-phi-5 right-phi-5 z-50 flex h-phi-chat-h max-h-[82vh] w-phi-chat max-w-[calc(100vw-2rem)] flex-col overflow-hidden rounded-phi-lg border border-[rgba(25,24,22,0.14)] bg-app-surface shadow-float';

  return (
    <div className={containerClass}>
      {/* Chat Header */}
      <div className="flex h-phi-bar shrink-0 items-center justify-between border-b border-[rgba(25,24,22,0.08)] bg-paper-50 px-phi-4">
        <div className="flex min-w-0 items-center gap-phi-3">
          <MessageSquare className="h-4 w-4 shrink-0 text-ink-muted" strokeWidth={1.5} />
          <div className="min-w-0">
            <h3 className="truncate text-phi-sm font-medium text-ink-primary">
              {documentId ? 'Document chat' : 'Library chat'}
            </h3>
          </div>
          {currentPage && (
            <span className="font-mono text-phi-2xs tabular-nums text-accent-ink">
              p. {currentPage}
            </span>
          )}
        </div>

        <div className="flex items-center gap-phi-1">
          <button
            type="button"
            onClick={() => setShowHistory(true)}
            className="inline-flex h-phi-ctrl-sm w-phi-ctrl-sm items-center justify-center rounded-phi-sm text-ink-muted transition-colors duration-phi-fast hover:bg-paper-200 hover:text-ink-primary"
            title="Chat history"
            aria-label="Chat history"
          >
            <History className="h-4 w-4" strokeWidth={1.5} />
          </button>
          {onToggleMinimize && (
            <button
              type="button"
              onClick={onToggleMinimize}
              className="inline-flex h-phi-ctrl-sm w-phi-ctrl-sm items-center justify-center rounded-phi-sm text-ink-muted transition-colors duration-phi-fast hover:bg-paper-200 hover:text-ink-primary"
              title="Hide chat"
              aria-label="Hide chat"
            >
              <Minimize2 className="h-4 w-4" strokeWidth={1.5} />
            </button>
          )}
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="inline-flex h-phi-ctrl-sm w-phi-ctrl-sm items-center justify-center rounded-phi-sm text-ink-muted transition-colors duration-phi-fast hover:bg-paper-200 hover:text-ink-primary"
              title="Close chat"
              aria-label="Close chat"
            >
              <X className="h-4 w-4" strokeWidth={1.5} />
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div
        ref={messagesContainerRef}
        className="flex-1 space-y-phi-4 overflow-y-auto bg-app-surface p-phi-4 scrollbar-thin"
      >
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex flex-col ${message.role === 'user' ? 'items-end' : 'items-start'}`}
          >
            <div
              className={`max-w-[90%] rounded-phi-md px-phi-4 py-phi-3 text-phi-sm ${
                message.role === 'user'
                  ? 'bg-ink-primary text-paper-50'
                  : 'border border-[rgba(25,24,22,0.09)] bg-paper-50 text-ink-primary'
              }`}
            >
              {message.role === 'user' ? (
                <p className="whitespace-pre-wrap break-words leading-phi">{message.content}</p>
              ) : (
                <div
                  className="prose prose-sm max-w-none
                    prose-headings:mt-3 prose-headings:mb-1.5 prose-headings:font-medium prose-headings:text-ink-primary
                    prose-p:my-1.5 prose-p:leading-phi prose-p:text-ink-primary
                    prose-strong:font-medium prose-strong:text-ink-primary
                    prose-ul:my-1.5 prose-ul:pl-4 prose-ol:my-1.5 prose-ol:pl-4
                    prose-li:my-0.5 prose-li:text-ink-secondary
                    prose-a:text-accent-ink prose-a:no-underline hover:prose-a:underline
                    prose-code:rounded prose-code:bg-paper-200 prose-code:px-1 prose-code:font-mono prose-code:text-phi-xs prose-code:text-ink-primary
                    prose-hr:my-3 prose-hr:border-[rgba(25,24,22,0.09)]"
                >
                  <ReactMarkdown>{message.content}</ReactMarkdown>
                </div>
              )}
            </div>

            <span className="mt-phi-1 font-mono text-phi-2xs tabular-nums text-ink-faint">
              {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>

            {message.role === 'assistant' &&
              message.relatedDocuments &&
              message.relatedDocuments.length > 0 && (
                <div className="mt-phi-2 w-full max-w-[92%] space-y-phi-2 rounded-phi-md border border-[rgba(25,24,22,0.09)] bg-paper-50 p-phi-3">
                  <p className="flex items-center gap-phi-2 px-phi-1 text-phi-2xs font-medium text-ink-muted">
                    <FileText className="h-3 w-3" strokeWidth={1.5} />
                    Referenced passages
                  </p>
                  {message.relatedDocuments.slice(0, 3).map((doc, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => handleNavigateToDocument(doc.document_id, doc.page_number || 1)}
                      className="folio-mark group w-full rounded-phi-sm border border-[rgba(25,24,22,0.08)] bg-app-surface py-phi-2 pl-phi-3 pr-phi-3 text-left transition-colors duration-phi-fast hover:border-[rgba(25,24,22,0.2)]"
                    >
                      <div className="flex items-center justify-between gap-phi-2">
                        <span className="truncate text-phi-xs font-medium text-ink-primary group-hover:text-accent-ink">
                          {doc.document_name || 'Document'}
                        </span>
                        <span className="flex shrink-0 items-center gap-phi-1 font-mono text-phi-2xs tabular-nums text-ink-muted">
                          {doc.page_number ? `p. ${doc.page_number}` : ''}
                          <ExternalLink
                            className="h-3 w-3 opacity-0 transition-opacity duration-phi-fast group-hover:opacity-100"
                            strokeWidth={1.5}
                          />
                        </span>
                      </div>
                      <p className="mt-phi-1 line-clamp-2 text-phi-2xs leading-phi text-ink-secondary">
                        {doc.text || 'Open referenced page'}
                      </p>
                    </button>
                  ))}
                </div>
              )}
          </div>
        ))}

        {isLoading && (
          <div className="flex items-center gap-phi-2 text-phi-xs text-ink-muted">
            <Loader2 className="h-3.5 w-3.5 animate-spin" strokeWidth={1.5} />
            <span>Drafting grounded answer</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Chat Excerpt Selection Popover */}
      {selectedChatText && selectionMenuPosition && (
        <div
          data-chat-selection-ignore="true"
          className="fixed z-[70] flex items-center gap-phi-1 rounded-phi-md border border-[rgba(25,24,22,0.16)] bg-ink-primary p-phi-1 text-paper-50 shadow-float"
          onMouseDown={(event) => event.preventDefault()}
          style={{
            left: `${selectionMenuPosition.x}px`,
            top: `${selectionMenuPosition.y}px`,
            transform: 'translate(-50%, -100%)',
          }}
        >
          <button
            type="button"
            onClick={askAboutSelectedChatText}
            className="flex items-center gap-phi-2 rounded-phi-sm bg-accent px-phi-3 py-phi-1 text-phi-xs font-medium text-white transition-colors duration-phi-fast hover:bg-accent-hover"
          >
            <MessageSquare className="h-3.5 w-3.5" strokeWidth={1.5} />
            Ask follow-up
          </button>
          <button
            type="button"
            onClick={copySelectedChatText}
            className="flex items-center gap-phi-2 rounded-phi-sm px-phi-3 py-phi-1 text-phi-xs font-medium text-paper-100 transition-colors duration-phi-fast hover:bg-white/10"
          >
            {copiedSelection ? (
              <>
                <Check className="h-3.5 w-3.5 text-[#4cc38a]" strokeWidth={1.5} />
                Copied
              </>
            ) : (
              <>
                <Copy className="h-3.5 w-3.5" strokeWidth={1.5} />
                Copy
              </>
            )}
          </button>
        </div>
      )}

      {/* Composer */}
      <div className="shrink-0 border-t border-[rgba(25,24,22,0.08)] bg-paper-50 p-phi-3">
        <div className="flex items-end gap-phi-2">
          <textarea
            ref={inputRef}
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder={documentId ? 'Ask about this document' : 'Ask across your library'}
            rows={2}
            className="max-h-28 min-h-[2.618rem] flex-1 resize-none rounded-phi-md border border-[rgba(25,24,22,0.14)] bg-app-surface px-phi-3 py-phi-2 text-phi-sm text-ink-primary placeholder:text-ink-faint focus:border-ink-primary focus:outline-none focus:ring-2 focus:ring-accent/15"
            disabled={isLoading}
          />
          <button
            type="button"
            onClick={sendMessage}
            disabled={!inputMessage.trim() || isLoading}
            className="btn-primary h-phi-ctrl w-phi-ctrl shrink-0 p-0"
            aria-label="Send message"
          >
            {isLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" strokeWidth={1.5} />
            ) : (
              <Send className="h-4 w-4" strokeWidth={1.5} />
            )}
          </button>
        </div>
        {documentContext && (
          <p className="mt-phi-2 truncate font-mono text-phi-2xs text-ink-muted">
            {documentContext}
          </p>
        )}
      </div>

      {showHistory && (
        <ChatHistory
          activeSessionId={sessionId}
          onDeleteSession={handleSessionDeleted}
          onLoadSession={loadSession}
          onClose={() => setShowHistory(false)}
        />
      )}
    </div>
  );
};

export default SimpleChatbot;
