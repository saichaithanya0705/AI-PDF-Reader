-- =============================================================================
-- Chat History Tables for Supabase
-- =============================================================================

-- Create chat_sessions table
CREATE TABLE IF NOT EXISTS public.chat_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT,
    context_type TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create chat_messages table
CREATE TABLE IF NOT EXISTS public.chat_messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    FOREIGN KEY (session_id) REFERENCES public.chat_sessions (id) ON DELETE CASCADE
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_sessions_user 
ON public.chat_sessions(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_messages_session 
ON public.chat_messages(session_id, created_at ASC);

-- Enable Row Level Security (RLS)
ALTER TABLE public.chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;

-- RLS Policies for chat_sessions
-- Users can only see their own sessions
CREATE POLICY "Users can view their own sessions"
ON public.chat_sessions FOR SELECT
USING (auth.uid()::TEXT = user_id);

CREATE POLICY "Users can create their own sessions"
ON public.chat_sessions FOR INSERT
WITH CHECK (auth.uid()::TEXT = user_id);

CREATE POLICY "Users can update their own sessions"
ON public.chat_sessions FOR UPDATE
USING (auth.uid()::TEXT = user_id);

CREATE POLICY "Users can delete their own sessions"
ON public.chat_sessions FOR DELETE
USING (auth.uid()::TEXT = user_id);

-- RLS Policies for chat_messages
-- Users can only see messages from their sessions
CREATE POLICY "Users can view their own messages"
ON public.chat_messages FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM public.chat_sessions
        WHERE chat_sessions.id = chat_messages.session_id
        AND chat_sessions.user_id = auth.uid()::TEXT
    )
);

CREATE POLICY "Users can create messages in their sessions"
ON public.chat_messages FOR INSERT
WITH CHECK (
    EXISTS (
        SELECT 1 FROM public.chat_sessions
        WHERE chat_sessions.id = chat_messages.session_id
        AND chat_sessions.user_id = auth.uid()::TEXT
    )
);

CREATE POLICY "Users can update their own messages"
ON public.chat_messages FOR UPDATE
USING (
    EXISTS (
        SELECT 1 FROM public.chat_sessions
        WHERE chat_sessions.id = chat_messages.session_id
        AND chat_sessions.user_id = auth.uid()::TEXT
    )
);

CREATE POLICY "Users can delete their own messages"
ON public.chat_messages FOR DELETE
USING (
    EXISTS (
        SELECT 1 FROM public.chat_sessions
        WHERE chat_sessions.id = chat_messages.session_id
        AND chat_sessions.user_id = auth.uid()::TEXT
    )
);
