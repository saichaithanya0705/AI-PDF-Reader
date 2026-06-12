import React, { useCallback, useEffect, useState } from 'react';
import { X, Clock, Trash2, MessageSquare, ChevronRight } from 'lucide-react';
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

    const handleLoadSession = useCallback(async (sessionId: string) => {
        setLoadingSessionId(sessionId);
        try {
            await onLoadSession(sessionId);
            onClose();
        } catch (err) {
            console.error('Error loading session from history:', err);
        } finally {
            setLoadingSessionId(null);
        }
    }, [onClose, onLoadSession]);

    const handleDeleteSession = useCallback(async (sessionId: string) => {
        if (!confirm('Are you sure you want to delete this chat session?')) {
            return;
        }

        try {
            setDeletingSessionId(sessionId);
            await deleteChatSession(sessionId);
            setSessions((currentSessions) => currentSessions.filter((session) => session.id !== sessionId));
            onDeleteSession?.(sessionId);
        } catch (err) {
            console.error('Error deleting session:', err);
            alert('Failed to delete session');
        } finally {
            setDeletingSessionId(null);
        }
    }, [onDeleteSession]);

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
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
            <div className="bg-slate-900 rounded-2xl shadow-2xl border border-slate-700 w-full max-w-2xl max-h-[80vh] flex flex-col m-4">
                {/* Header */}
                <div className="bg-gradient-to-r from-blue-600 to-purple-600 p-6 rounded-t-2xl flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="bg-white/20 rounded-full p-2">
                            <Clock className="w-6 h-6 text-white" />
                        </div>
                        <div>
                            <h2 className="text-white font-semibold text-xl">Chat History</h2>
                            <p className="text-white/80 text-sm">View and manage your conversations</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="text-white/80 hover:text-white p-2 hover:bg-white/10 rounded-lg transition-colors"
                    >
                        <X className="w-6 h-6" />
                    </button>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6">
                    {loading && (
                        <div className="text-center text-slate-400 py-12">
                            <div className="animate-spin rounded-full h-12 w-12 border-4 border-blue-500 border-t-transparent mx-auto mb-4"></div>
                            <p>Loading chat history...</p>
                        </div>
                    )}

                    {error && (
                        <div className="text-center text-red-400 py-12">
                            <p>{error}</p>
                            <button
                                onClick={loadSessions}
                                className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
                            >
                                Try Again
                            </button>
                        </div>
                    )}

                    {!loading && !error && sessions.length === 0 && (
                        <div className="text-center text-slate-400 py-12">
                            <MessageSquare className="w-16 h-16 mx-auto mb-4 opacity-50" />
                            <p className="text-lg font-medium">No chat history yet</p>
                            <p className="text-sm mt-2">Start a conversation to see it here!</p>
                        </div>
                    )}

                    {!loading && !error && sessions.length > 0 && (
                        <div className="space-y-3">
                            {sessions.map((session) => (
                                <div
                                    key={session.id}
                                    className={`group flex items-stretch gap-3 rounded-xl border p-2 transition-all duration-200 ${
                                        activeSessionId === session.id
                                            ? 'border-cyan-500 bg-slate-800/95'
                                            : 'border-slate-700 bg-slate-800 hover:bg-slate-700'
                                    }`}
                                >
                                    <button
                                        type="button"
                                        onClick={() => void handleLoadSession(session.id)}
                                        disabled={Boolean(loadingSessionId || deletingSessionId)}
                                        className="flex flex-1 items-start justify-between gap-3 rounded-lg p-2 text-left transition-colors disabled:cursor-not-allowed disabled:opacity-70"
                                    >
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2 mb-1">
                                                <MessageSquare className="w-4 h-4 text-cyan-400 flex-shrink-0" />
                                                <h3 className="text-white font-medium truncate">
                                                    {session.title}
                                                </h3>
                                            </div>

                                            <div className="flex items-center gap-3 text-xs text-slate-400">
                                                <span className="flex items-center gap-1">
                                                    <Clock className="w-3 h-3" />
                                                    {loadingSessionId === session.id ? 'Loading...' : formatDate(session.updated_at)}
                                                </span>
                                                <span className="px-2 py-0.5 bg-slate-700 rounded text-slate-300">
                                                    {session.context_type === 'library' ? '📚 Library' : '📄 PDF'}
                                                </span>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-2 flex-shrink-0">
                                            <ChevronRight className="w-5 h-5 text-slate-500 group-hover:text-cyan-400 transition-colors" />
                                        </div>
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => void handleDeleteSession(session.id)}
                                        disabled={Boolean(loadingSessionId || deletingSessionId)}
                                        className="self-center rounded-lg p-3 text-slate-400 transition-colors hover:bg-red-400/10 hover:text-red-400 disabled:cursor-not-allowed disabled:opacity-60"
                                        title="Delete session"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-4 border-t border-slate-700 bg-slate-800/50 rounded-b-2xl">
                    <p className="text-center text-xs text-slate-400">
                        {sessions.length} session{sessions.length !== 1 ? 's' : ''} total
                    </p>
                </div>
            </div>
        </div>
    );
};

export default ChatHistory;
