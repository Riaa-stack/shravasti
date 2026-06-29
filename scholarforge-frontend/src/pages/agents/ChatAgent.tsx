import { useState, useEffect, useRef } from 'react';
import { useChatStore, type ChatMessage } from '@/store/chatStore';
import { usePaperStore } from '@/store/paperStore';
import { useAuthStore } from '@/store/authStore';
import { Send, Bot, User as UserIcon, Loader2, AlertCircle } from 'lucide-react';
import { GoogleLoader } from '@/components/ui/GoogleLoader';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeHighlight from 'rehype-highlight';

export function ChatAgent() {
  const [input, setInput] = useState('');
  const [sessionId] = useState(() => crypto.randomUUID());
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { messages, addMessage, appendToken, isTyping, setTyping } = useChatStore();
  const selectedPaperIds = usePaperStore(state => state.selectedPaperIds);
  const user = useAuthStore(state => state.user);

  useEffect(() => {
    // Scroll to bottom on new message
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  useEffect(() => {
    const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';
    const ws = new WebSocket(`${wsUrl}/chat/${sessionId}`);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'status') {
        setTyping(true);
      } else if (data.type === 'token') {
        setTyping(false);
        appendToken('current_assistant_msg', data.token);
      } else if (data.type === 'source') {
        // Handle sources if needed
      } else if (data.type === 'complete') {
        setTyping(false);
      } else if (data.type === 'error') {
        setTyping(false);
        // Handle error
      }
    };

    wsRef.current = ws;

    return () => {
      ws.close();
    };
  }, [sessionId]);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !wsRef.current) return;

    const userMsg: ChatMessage = { id: crypto.randomUUID(), role: 'user', content: input };
    addMessage(userMsg);

    // Add empty assistant message to stream into
    addMessage({ id: 'current_assistant_msg', role: 'assistant', content: '' });

    wsRef.current.send(JSON.stringify({
      query: input,
      paper_ids: selectedPaperIds,
      user_id: user?.id
    }));

    setInput('');
    setTyping(true);
  };

  return (
    <div className="flex flex-col h-full bg-background/50">
      <div className="p-4 border-b border-border/50 bg-card/50">
        <h2 className="font-semibold font-display">Research Chat Assistant</h2>
        <p className="text-xs text-muted-foreground mt-1">
          Chatting with {selectedPaperIds.length} selected papers in context.
        </p>
      </div>

      {selectedPaperIds.length === 0 && (
        <div className="m-4 p-3 bg-amber-500/10 border border-amber-500/20 text-amber-500 rounded-lg flex items-center gap-2 text-sm">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          No papers selected. Responses will rely on general knowledge.
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {messages.map((msg, idx) => {
          const isUser = msg.role === 'user';
          // Hide empty assistant messages that haven't received tokens yet
          if (!isUser && msg.content === '' && isTyping) return null;

          return (
            <div key={idx} className={`flex gap-4 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
              <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${isUser ? 'bg-gradient-to-br from-google-blue to-google-blue/80 text-white shadow-md' : 'bg-card text-foreground border border-border shadow-sm'}`}>
                {isUser ? <UserIcon className="w-4 h-4" /> : <Bot className="w-4 h-4 text-google-blue" />}
              </div>
              <div className={`max-w-[80%] rounded-2xl p-4 ${isUser ? 'bg-gradient-to-br from-google-blue to-blue-600 text-white shadow-md' : 'bg-card border border-border/50 shadow-sm relative overflow-hidden'}`}>
                {!isUser && <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-google-blue via-google-red to-google-yellow" />}
                <div className={`prose prose-sm ${isUser ? 'prose-invert max-w-none' : 'dark:prose-invert max-w-none'}`}>
                  <ReactMarkdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeHighlight]}>
                    {msg.content}
                  </ReactMarkdown>
                </div>
              </div>
            </div>
          );
        })}
        {isTyping && (
          <div className="flex gap-4">
            <div className="w-8 h-8 rounded-full bg-card text-foreground border border-border shadow-sm flex items-center justify-center flex-shrink-0">
              <Bot className="w-4 h-4 text-google-blue" />
            </div>
            <div className="bg-card border border-border/50 rounded-2xl p-4 flex items-center gap-3 relative overflow-hidden shadow-sm">
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-google-blue via-google-red to-google-yellow animate-pulse" />
              <GoogleLoader size="sm" />
              <span className="text-sm text-muted-foreground font-medium">Synthesizing response...</span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 border-t border-border/50 bg-card/30 relative z-20">
        <form onSubmit={handleSend} className="relative max-w-4xl mx-auto group">
          <div className="absolute -inset-0.5 bg-gradient-to-r from-google-blue via-google-red to-google-yellow rounded-full blur opacity-30 group-focus-within:opacity-75 transition duration-500 group-focus-within:duration-200 animate-pulse-slow"></div>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about your research..."
            className="relative w-full bg-background border-none rounded-full pl-6 pr-14 py-4 focus:outline-none shadow-sm"
          />
          <button
            type="submit"
            disabled={!input.trim() || isTyping}
            className="absolute right-2 top-1/2 -translate-y-1/2 p-2.5 bg-google-blue hover:bg-google-blue/90 text-white rounded-full transition-colors disabled:opacity-50 shadow-md"
          >
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
}
