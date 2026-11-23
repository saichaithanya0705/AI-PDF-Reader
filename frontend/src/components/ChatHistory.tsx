import React, { useCallback, useEffect, useState } from 'react';
import { X, Clock, Trash2, MessageSquare, ChevronRight, Loader2 } from 'lucide-react';
import { deleteChatSession, listChatSessions, type ChatSessionSummary } from '../lib/api';

interface ChatHistoryProps {
  onLoadSession: (sessionId: string) => Promise<void>;
  onClose: () => void;
  activeSessionId?: string | null;
  onDeleteSession?: (sessionId: string) => void;
}

const ChatHistory: React.FC<ChatHistoryProps> = ({
  onLoadSession,
  onClose,
  activeSessionId = null,
  onDeleteSession,
}) => {
  const [sessions, setSessions] = useState<ChatSessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingSessionId, setLoadingSessionId] = useState<string | null>(null);
  const [deletingSessionId, setDeletingSessionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadSessions = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const data = await listChatSessions();
      setSessions(data.sessions);
    } catch (err) {
      console.error('Error loading chat sessions:', err);
      setError('Failed to load chat history');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  const handleLoadSession = useCallback(
    async (sessionId: string) => {
      setLoadingSessionId(sessionId);
      try {
        await onLoadSession(sessionId);
        onClose();
      } catch (err) {
        console.error('Error loading session from history:', err);
      } finally {
        setLoadingSessionId(null);
      }
    },
    [onClose, onLoadSession]
  );

  const handleDeleteSession = useCallback(
    async (sessionId: string) => {
      if (!confirm('Delete this chat session?')) {
        return;
      }

      try {
        setDeletingSessionId(sessionId);
        await deleteChatSession(sessionId);
        setSessions((currentSessions) =>
          currentSessions.filter((session) => session.id !== sessionId)
        );
        onDeleteSession?.(sessionId);
      } catch (err) {
        console.error('Error deleting session:', err);
        alert('Failed to delete session');
      } finally {
        setDeletingSessionId(null);
      }
    },
    [onDeleteSession]
  );

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink-primary/35 p-phi-4 backdrop-blur-[2px]">
      <div className="flex max-h-[80vh] w-full max-w-phi-modal-lg flex-col overflow-hidden rounded-phi-lg border border-[rgba(25,24,22,0.12)] bg-app-surface shadow-float">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-[rgba(25,24,22,0.08)] px-phi-5 py-phi-4">
          <div>
            <h2 className="font-serif text-phi-lg font-normal text-ink-primary">Chat history</h2>
            <p className="mt-phi-1 text-phi-xs text-ink-muted">Resume or delete past conversations</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-phi-sm p-phi-2 text-ink-muted transition-colors duration-phi-fast hover:bg-paper-200 hover:text-ink-primary"
            aria-label="Close chat history"
          >
            <X className="h-4 w-4" strokeWidth={1.5} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-phi-4 scrollbar-thin">
          {loading && (
            <div className="flex items-center justify-center gap-phi-2 py-phi-6 text-phi-sm text-ink-secondary">
              <Loader2 className="h-4 w-4 animate-spin text-ink-muted" strokeWidth={1.5} />
              Loading conversations
            </div>
          )}

          {error && (
            <div className="py-phi-6 text-center">
              <p className="text-phi-sm text-semantic-negative">{error}</p>
              <button
                type="button"
                onClick={loadSessions}
                className="btn-secondary mt-phi-3 h-phi-ctrl-sm text-phi-xs"
              >
                Try again
              </button>
            </div>
          )}

          {!loading && !error && sessions.length === 0 && (
            <div className="py-phi-6 text-center">
              <MessageSquare className="mx-auto h-5 w-5 text-ink-faint" strokeWidth={1.5} />
              <p className="mt-phi-3 text-phi-sm font-medium text-ink-primary">No saved conversations</p>
              <p className="mt-phi-1 text-phi-xs text-ink-muted">
                Questions you ask in the library or reader will appear here.
              </p>
            </div>
          )}

          {!loading && !error && sessions.length > 0 && (
            <div className="space-y-phi-2">
              {sessions.map((session) => {
                const isActive = activeSessionId === session.id;
                return (
                  <div
                    key={session.id}
                    className={`group flex items-center gap-phi-2 rounded-phi-md border p-phi-2 transition-colors duration-phi-fast ${
                      isActive
                        ? 'folio-mark border-[rgba(25,24,22,0.18)] bg-paper-50 pl-phi-3'
                        : 'border-[rgba(25,24,22,0.08)] bg-app-surface hover:border-[rgba(25,24,22,0.18)] hover:bg-paper-50/70'
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => void handleLoadSession(session.id)}
                      disabled={Boolean(loadingSessionId || deletingSessionId)}
                      className="flex min-w-0 flex-1 items-center justify-between gap-phi-3 rounded-phi-sm p-phi-2 text-left disabled:opacity-60"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-phi-sm font-medium text-ink-primary">
                          {session.title}
                        </p>
                        <div className="mt-phi-1 flex items-center gap-phi-3 font-mono text-phi-2xs text-ink-muted">
                          <span className="inline-flex items-center gap-phi-1 tabular-nums">
                            <Clock className="h-3 w-3" strokeWidth={1.5} />
                            {loadingSessionId === session.id
                              ? 'Loading'
                              : formatDate(session.updated_at)}
                          </span>
                          <span>·</span>
                          <span>{session.context_type === 'library' ? 'Library' : 'PDF'}</span>
                        </div>
                      </div>
                      <ChevronRight
                        className="h-4 w-4 shrink-0 text-ink-faint transition-colors duration-phi-fast group-hover:text-ink-primary"
                        strokeWidth={1.5}
                      />
                    </button>

                    <button
                      type="button"
                      onClick={() => void handleDeleteSession(session.id)}
                      disabled={Boolean(loadingSessionId || deletingSessionId)}
                      className="rounded-phi-sm p-phi-2 text-ink-muted transition-colors duration-phi-fast hover:bg-semantic-negativeBg hover:text-semantic-negative disabled:opacity-50"
                      title="Delete session"
                      aria-label={`Delete ${session.title}`}
                    >
                      <Trash2 className="h-4 w-4" strokeWidth={1.5} />
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-[rgba(25,24,22,0.08)] bg-paper-50 px-phi-5 py-phi-3">
          <p className="font-mono text-phi-xs tabular-nums text-ink-muted">
            {sessions.length} session{sessions.length !== 1 ? 's' : ''}
          </p>
        </div>
      </div>
    </div>
  );
};

export default ChatHistory;
