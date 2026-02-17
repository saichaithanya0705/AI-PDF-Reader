import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, Send, X, Loader2, Bot, User, Minimize2, Maximize2 } from 'lucide-react';
import { API_URL } from '../config';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface SimpleChatbotProps {
  documentId?: string;
  documentContext?: string;
  onClose?: () => void;
  isMinimized?: boolean;
  onToggleMinimize?: () => void;
  initialMessage?: string;
}

const SimpleChatbot: React.FC<SimpleChatbotProps> = ({ 
  documentId, 
  documentContext, 
  onClose,
  isMinimized = false,
  onToggleMinimize,
  initialMessage
}) => {
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
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

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
      // Auto-focus the input so user can immediately send or edit
      setTimeout(() => {
        inputRef.current?.focus();
      }, 100);
    }
  }, [initialMessage, isMinimized]);

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
  const response = await fetch(`${API_URL}/api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: inputMessage,
          document_id: documentId,
          document_context: documentContext,
          conversation_history: messages.slice(-5).map(m => ({
            role: m.role,
            content: m.content
          }))
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      const assistantMessage: Message = {
        role: 'assistant',
        content: data.response || 'I apologize, but I encountered an issue processing your request.',
        timestamp: new Date()
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

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  if (isMinimized) {
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

  return (
    <div className="fixed bottom-6 right-6 w-96 h-[600px] bg-slate-900 rounded-2xl shadow-2xl border border-slate-700 flex flex-col z-50 overflow-hidden">
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
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-900">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex gap-3 ${message.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
          >
            <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
              message.role === 'user' 
                ? 'bg-blue-600' 
                : 'bg-gradient-to-br from-purple-600 to-blue-600'
            }`}>
              {message.role === 'user' ? (
                <User className="w-4 h-4 text-white" />
              ) : (
                <Bot className="w-4 h-4 text-white" />
              )}
            </div>
            <div className={`flex-1 max-w-[80%] ${
              message.role === 'user' ? 'text-right' : 'text-left'
            }`}>
              <div className={`inline-block rounded-2xl px-4 py-2 ${
                message.role === 'user'
                  ? 'bg-blue-600 text-white rounded-br-none'
                  : 'bg-slate-800 text-slate-200 rounded-bl-none border border-slate-700'
              }`}>
                <p className="text-sm whitespace-pre-wrap break-words">{message.content}</p>
              </div>
              <p className="text-xs text-slate-500 mt-1">
                {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
              </p>
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

      {/* Input */}
      <div className="p-4 bg-slate-800 border-t border-slate-700">
        <div className="flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message..."
            className="flex-1 bg-slate-900 text-white rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 border border-slate-700 placeholder-slate-500"
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
    </div>
  );
};

export default SimpleChatbot;
