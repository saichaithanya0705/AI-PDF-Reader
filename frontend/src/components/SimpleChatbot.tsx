import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, Send, X, Loader2, Bot, User, Minimize2, History, FileText, ExternalLink, Copy, Check } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import ChatHistory from './ChatHistory';
import { apiRequest } from '../lib/api';

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

interface ChatMessageRecord {
  role?: unknown;
  content?: unknown;
  created_at?: unknown;
  metadata?: {
    sources?: unknown;
    search_results?: unknown;
  };
}

const SimpleChatbot: React.FC<SimpleChatbotProps> = ({
  documentId,
  documentContext,
  currentPage,
  viewType,
  onClose,
  isMinimized = false,
  onToggleMinimize,
  initialMessage,
  variant = 'floating'
}) => {
  const navigate = useNavigate();
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: documentContext
        ? 'Hi! I can help you understand this document. Ask me anything about it!'
        : 'Hi! I\'m your AI assistant. How can I help you today?',
      timestamp: new Date()
    }
  ]);
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

  // Handle initial message - populate input when provided
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
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const data = await apiRequest<Record<string, unknown>>('/api/chat', {
        method: 'POST',
        body: JSON.stringify({
          message: inputMessage,
          document_id: documentId,
          current_page: currentPage,
          context_type: viewType || (documentId ? 'pdf_viewer' : 'library'),
          session_id: sessionId,  // NEW: Include session ID for history tracking
          conversation_history: messages.slice(-5).map(m => ({
            role: m.role,
            content: m.content
          }))
        }),
      });

      // Update session ID if it was created
      if (typeof data.session_id === 'string' && !sessionId) {
        setSessionId(data.session_id);
      }

      // Extract related documents from the new dedicated field, sources, or search_results
      const context = typeof data.context === 'object' && data.context !== null
        ? data.context as Record<string, unknown>
        : {};
      const relatedDocs = normalizeRelatedDocuments(
        data.related_documents || data.sources || context.search_results || context.related_documents
      );

      const assistantMessage: Message = {
        role: 'assistant',
        content: typeof data.response === 'string'
          ? data.response
          : 'I apologize, but I encountered an issue processing your request.',
        timestamp: new Date(),
        relatedDocuments: relatedDocs
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Chat error:', error);

      const errorMessage: Message = {
        role: 'assistant',
        content: 'Sorry, I\'m having trouble connecting right now. Please try again.',
        timestamp: new Date()
      };

      setMessages(prev => [...prev, errorMessage]);
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
      const data = await apiRequest<Record<string, unknown>>(`/api/chat/sessions/${sessionIdToLoad}`);
      const historyMessages = Array.isArray(data.messages) ? data.messages : [];

      // Convert messages from history format to Message format
      const loadedMessages: Message[] = historyMessages
        .filter((message): message is ChatMessageRecord => typeof message === 'object' && message !== null)
        .map((message) => ({
          role: message.role === 'user' ? 'user' : 'assistant',
          content: typeof message.content === 'string' ? message.content : '',
          timestamp: typeof message.created_at === 'string' ? new Date(message.created_at) : new Date(),
          relatedDocuments: normalizeRelatedDocuments(message.metadata?.sources || message.metadata?.search_results),
        }));

      setMessages(loadedMessages);
      setSessionId(sessionIdToLoad);
    } catch (error) {
      console.error('Error loading session:', error);
      alert('Failed to load chat session');
    }
  };

  const handleNavigateToDocument = (docId: string, page: number) => {
    navigate(`/reader/${docId}?page=${page}`);
  };

  if (isMinimized) {
    if (variant === 'docked') {
      return null;
    }

    return (
      <div className="fixed bottom-6 right-6 z-50">
        <button
          onClick={onToggleMinimize}
          className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white rounded-full p-4 shadow-2xl transition-all duration-300 hover:scale-110 group relative"
        >
          <MessageSquare className="w-6 h-6" />
          {messages.length > 1 && (
            <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center animate-pulse">
              {messages.length - 1}
            </span>
          )}
          <span className="absolute bottom-full right-0 mb-2 bg-slate-800 text-white text-sm px-3 py-1 rounded-lg whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity">
            Chat with AI
          </span>
        </button>
      </div>
    );
  }

  const containerClass = variant === 'docked'
    ? 'h-full w-full bg-slate-900 border-l border-slate-700 flex flex-col overflow-hidden'
    : 'fixed bottom-6 right-6 w-96 h-[600px] bg-slate-900 rounded-2xl shadow-2xl border border-slate-700 flex flex-col z-50 overflow-hidden';

  return (
    <div className={containerClass}>
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-purple-600 p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="bg-white/20 rounded-full p-2">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <h3 className="text-white font-semibold">AI Assistant</h3>
            <p className="text-white/80 text-xs">
              {isLoading ? 'Typing...' : 'Online'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowHistory(true)}
            className="text-white/80 hover:text-white p-1 hover:bg-white/10 rounded transition-colors"
            title="Chat History"
          >
            <History className="w-4 h-4" />
          </button>
          {onToggleMinimize && (
            <button
              onClick={onToggleMinimize}
              className="text-white/80 hover:text-white p-1 hover:bg-white/10 rounded transition-colors"
              title="Minimize"
            >
              <Minimize2 className="w-4 h-4" />
            </button>
          )}
          {onClose && (
            <button
              onClick={onClose}
              className="text-white/80 hover:text-white p-1 hover:bg-white/10 rounded transition-colors"
              title="Close"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div ref={messagesContainerRef} className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-900">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex gap-3 ${message.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
          >
            <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${message.role === 'user'
              ? 'bg-blue-600'
              : 'bg-gradient-to-br from-purple-600 to-blue-600'
              }`}>
              {message.role === 'user' ? (
                <User className="w-4 h-4 text-white" />
              ) : (
                <Bot className="w-4 h-4 text-white" />
              )}
            </div>
            <div className={`flex-1 max-w-[85%] ${message.role === 'user' ? 'text-right' : 'text-left'
              }`}>
              <div className={`inline-block rounded-2xl px-4 py-2 ${message.role === 'user'
                ? 'bg-blue-600 text-white rounded-br-none'
                : 'bg-slate-800 text-slate-200 rounded-bl-none border border-slate-700'
                }`}>
                {message.role === 'user' ? (
                  <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>
                ) : (
                  <div className="text-sm prose prose-invert prose-sm max-w-none
                    prose-headings:text-slate-100 prose-headings:font-semibold prose-headings:mt-3 prose-headings:mb-2
                    prose-h1:text-base prose-h2:text-sm prose-h3:text-sm
                    prose-p:text-slate-200 prose-p:my-1.5 prose-p:leading-relaxed
                    prose-strong:text-cyan-300 prose-strong:font-semibold
                    prose-ul:my-2 prose-ul:pl-4 prose-ol:my-2 prose-ol:pl-4
                    prose-li:text-slate-200 prose-li:my-0.5 prose-li:marker:text-cyan-400
                    prose-a:text-cyan-400 prose-a:no-underline hover:prose-a:underline
                    prose-code:text-pink-300 prose-code:bg-slate-900/50 prose-code:px-1 prose-code:rounded
                    prose-hr:border-slate-600 prose-hr:my-3">
                    <ReactMarkdown>{message.content}</ReactMarkdown>
                  </div>
                )}
              </div>

              <p className="text-xs text-slate-500 mt-1">
                {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </p>

              {/* Related Documents Section - Only for assistant messages with related docs */}
              {message.role === 'assistant' && message.relatedDocuments && message.relatedDocuments.length > 0 && (
                <div className="mt-3 p-2 bg-slate-800/50 rounded-lg border border-slate-700/50">
                  <p className="text-xs text-slate-400 mb-2 flex items-center gap-1">
                    <FileText className="w-3 h-3" />
                    Related in your library:
                  </p>
                  <div className="space-y-1.5">
                    {message.relatedDocuments.slice(0, 3).map((doc, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleNavigateToDocument(doc.document_id, doc.page_number || 1)}
                        className="w-full text-left p-2 bg-slate-700/40 hover:bg-slate-700/70 rounded-lg transition-all group"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-cyan-400 font-medium truncate max-w-[200px]">
                            {doc.document_name || 'Document'}
                          </span>
                          <span className="text-[10px] text-slate-500 flex items-center gap-1">
                            <span className="bg-green-500/20 text-green-400 px-1.5 py-0.5 rounded">
                              {Math.round((doc.similarity || 0) * 100)}% match
                            </span>
                            <ExternalLink className="w-3 h-3 opacity-0 group-hover:opacity-100 transition-opacity" />
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">
                          {doc.text || 'Click to view this section'}
                        </p>
                        {doc.page_number && (
                          <span className="text-[10px] text-slate-500">Page {doc.page_number}</span>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex gap-3">
            <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-gradient-to-br from-purple-600 to-blue-600">
              <Bot className="w-4 h-4 text-white" />
            </div>
            <div className="bg-slate-800 rounded-2xl rounded-bl-none px-4 py-3 border border-slate-700">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                <span className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                <span className="w-2 h-2 bg-slate-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {selectedChatText && selectionMenuPosition && (
        <div
          data-chat-selection-ignore="true"
          className="fixed z-[70] flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-800 p-2 shadow-2xl"
          onMouseDown={(event) => event.preventDefault()}
          style={{
            left: `${selectionMenuPosition.x}px`,
            top: `${selectionMenuPosition.y}px`,
            transform: 'translate(-50%, -100%)',
          }}
        >
          <button
            onClick={askAboutSelectedChatText}
            className="flex items-center gap-2 rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
            title="Ask AI about this chat excerpt"
          >
            <MessageSquare className="h-4 w-4" />
            Ask AI
          </button>
          <button
            onClick={copySelectedChatText}
            className="flex items-center gap-2 rounded-md bg-slate-700 px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-slate-600"
            title="Copy selected chat text"
          >
            {copiedSelection ? (
              <>
                <Check className="h-4 w-4 text-green-400" />
                <span>Copied</span>
              </>
            ) : (
              <>
                <Copy className="h-4 w-4" />
                <span>Copy</span>
              </>
            )}
          </button>
        </div>
      )}

      {/* Input */}
      <div className="p-4 bg-slate-800 border-t border-slate-700">
        <div className="flex gap-2">
          <textarea
            ref={inputRef}
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="Type your message..."
            rows={2}
            className="max-h-28 min-h-[3rem] flex-1 resize-none rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isLoading}
          />
          <button
            onClick={sendMessage}
            disabled={!inputMessage.trim() || isLoading}
            className="bg-blue-600 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl px-4 py-3 transition-all duration-200 hover:scale-105 disabled:hover:scale-100"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
        {documentContext && (
          <p className="text-xs text-slate-500 mt-2 flex items-center gap-1">
            <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
            Chatting about current document
          </p>
        )}
      </div>

      {/* Chat History Modal */}
      {showHistory && (
        <ChatHistory
          onLoadSession={loadSession}
          onClose={() => setShowHistory(false)}
        />
      )}
    </div>
  );
};

export default SimpleChatbot;
