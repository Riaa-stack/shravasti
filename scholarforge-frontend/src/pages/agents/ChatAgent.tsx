import { useState, useEffect, useRef } from 'react';
import { useChatStore, type ChatMessage } from '@/store/chatStore';
import { usePaperStore } from '@/store/paperStore';
import { useAuthStore } from '@/store/authStore';
import {
  Send,
  Bot,
  User as UserIcon,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import { GoogleLoader } from '@/components/ui/GoogleLoader';
import ReactMarkdown from 'react-markdown';
import remarkMath from 'remark-math';
import rehypeHighlight from 'rehype-highlight';

export function ChatAgent() {
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const {
    messages,
    addMessage,
    isTyping,
    setTyping,
  } = useChatStore();

  const selectedPaperIds = usePaperStore(
    (state) => state.selectedPaperIds
  );

  const user = useAuthStore(
    (state) => state.user
  );

  // ============================================================
  // SCROLL TO BOTTOM
  // ============================================================

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({
      behavior: 'smooth',
    });
  }, [messages, isTyping]);

  // ============================================================
  // SEND CHAT MESSAGE
  // ============================================================

  const handleSend = async (
    e: React.FormEvent
  ) => {
    e.preventDefault();

    const query = input.trim();

    if (!query || isSending) {
      return;
    }

    // ----------------------------------------------------------
    // USER MESSAGE
    // ----------------------------------------------------------

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: query,
    };

    addMessage(userMsg);

    setInput('');
    setIsSending(true);
    setTyping(true);

    try {
      // --------------------------------------------------------
      // AUTH TOKEN
      // --------------------------------------------------------

      const token = localStorage.getItem(
        'access_token'
      ) ||
        localStorage.getItem(
          'neuromind_access_token'
        );

      // --------------------------------------------------------
      // API BASE URL
      // --------------------------------------------------------

      const apiBase =
        import.meta.env.VITE_API_BASE_URL ||
        'http://localhost:8000/api/v1';

      // --------------------------------------------------------
      // CALL EXISTING BACKEND CHAT API
      // --------------------------------------------------------

      const response = await fetch(
        `${apiBase}/agents/chat`,
        {
          method: 'POST',

          headers: {
            'Content-Type': 'application/json',

            ...(token
              ? {
                  Authorization: `Bearer ${token}`,
                }
              : {}),
          },

          body: JSON.stringify({
            query,
            paper_ids: selectedPaperIds,
            session_id: null,
          }),
        }
      );

      // --------------------------------------------------------
      // PARSE RESPONSE
      // --------------------------------------------------------

      const data = await response.json();

      if (!response.ok) {
        const errorMessage =
          data?.detail ||
          data?.message ||
          data?.error ||
          'Chat request failed.';

        throw new Error(
          typeof errorMessage === 'string'
            ? errorMessage
            : JSON.stringify(errorMessage)
        );
      }

      // --------------------------------------------------------
      // BACKEND RESPONSE
      //
      // {
      //   session_id: "...",
      //   response: "...",
      //   sources: [...]
      // }
      // --------------------------------------------------------

      const assistantContent =
        data?.response ??
        data?.result?.response ??
        '';

      if (!assistantContent) {
        throw new Error(
          'The backend returned an empty chatbot response.'
        );
      }

      // --------------------------------------------------------
      // SAVE ASSISTANT MESSAGE IN FRONTEND STORE
      // --------------------------------------------------------

      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: assistantContent,
      };

      addMessage(assistantMsg);

      // --------------------------------------------------------
      // SAVE SESSION ID LOCALLY
      //
      // The backend creates the real PostgreSQL ChatSession.
      // We keep its ID so future messages can belong to
      // the same conversation.
      // --------------------------------------------------------

      if (data?.session_id) {
        localStorage.setItem(
          'scholarforge_chat_session_id',
          data.session_id
        );
      }

      // --------------------------------------------------------
      // SOURCES
      // --------------------------------------------------------

      if (
        Array.isArray(data?.sources) &&
        data.sources.length > 0
      ) {
        console.log(
          'Chat sources:',
          data.sources
        );
      }
    } catch (error) {
      console.error(
        'Chat request failed:',
        error
      );

      const errorMessage =
        error instanceof Error
          ? error.message
          : 'Unable to get a response from the chatbot.';

      addMessage({
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `**Chatbot error:** ${errorMessage}`,
      });
    } finally {
      setTyping(false);
      setIsSending(false);
    }
  };

  // ============================================================
  // UI
  // ============================================================

  return (
    <div className="flex flex-col h-full bg-background/50">

      {/* ======================================================
          HEADER
      ====================================================== */}

      <div className="p-4 border-b border-border/50 bg-card/50">
        <h2 className="font-semibold font-display">
          Research Chat Assistant
        </h2>

        <p className="text-xs text-muted-foreground mt-1">
          Chatting with {selectedPaperIds.length} selected papers
          in context.
        </p>
      </div>

      {/* ======================================================
          NO PAPERS WARNING
      ====================================================== */}

      {selectedPaperIds.length === 0 && (
        <div className="m-4 p-3 bg-amber-500/10 border border-amber-500/20 text-amber-500 rounded-lg flex items-center gap-2 text-sm">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />

          <span>
            No papers selected. Responses will rely on
            general knowledge.
          </span>
        </div>
      )}

      {/* ======================================================
          MESSAGES
      ====================================================== */}

      <div className="flex-1 overflow-y-auto p-4 space-y-6">

        {messages.map((msg, idx) => {
          const isUser =
            msg.role === 'user';

          return (
            <div
              key={msg.id || idx}
              className={`flex gap-4 ${
                isUser
                  ? 'flex-row-reverse'
                  : 'flex-row'
              }`}
            >

              {/* AVATAR */}

              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                  isUser
                    ? 'bg-gradient-to-br from-google-blue to-google-blue/80 text-white shadow-md'
                    : 'bg-card text-foreground border border-border shadow-sm'
                }`}
              >
                {isUser ? (
                  <UserIcon className="w-4 h-4" />
                ) : (
                  <Bot className="w-4 h-4 text-google-blue" />
                )}
              </div>

              {/* MESSAGE */}

              <div
                className={`max-w-[80%] rounded-2xl p-4 ${
                  isUser
                    ? 'bg-gradient-to-br from-google-blue to-blue-600 text-white shadow-md'
                    : 'bg-card border border-border/50 shadow-sm relative overflow-hidden'
                }`}
              >

                {!isUser && (
                  <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-google-blue via-google-red to-google-yellow" />
                )}

                <div
                  className={`prose prose-sm ${
                    isUser
                      ? 'prose-invert max-w-none'
                      : 'dark:prose-invert max-w-none'
                  }`}
                >
                  <ReactMarkdown
                    remarkPlugins={[remarkMath]}
                    rehypePlugins={[rehypeHighlight]}
                  >
                    {msg.content}
                  </ReactMarkdown>
                </div>

              </div>
            </div>
          );
        })}

        {/* ====================================================
            TYPING INDICATOR
        ==================================================== */}

        {isTyping && (
          <div className="flex gap-4">

            <div className="w-8 h-8 rounded-full bg-card text-foreground border border-border shadow-sm flex items-center justify-center flex-shrink-0">
              <Bot className="w-4 h-4 text-google-blue" />
            </div>

            <div className="bg-card border border-border/50 rounded-2xl p-4 flex items-center gap-3 relative overflow-hidden shadow-sm">

              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-google-blue via-google-red to-google-yellow animate-pulse" />

              <GoogleLoader size="sm" />

              <span className="text-sm text-muted-foreground font-medium">
                Synthesizing response...
              </span>

            </div>
          </div>
        )}

        <div ref={messagesEndRef} />

      </div>

      {/* ======================================================
          INPUT
      ====================================================== */}

      <div className="p-4 border-t border-border/50 bg-card/30 relative z-20">

        <form
          onSubmit={handleSend}
          className="relative max-w-4xl mx-auto group"
        >

          <div className="absolute -inset-0.5 bg-gradient-to-r from-google-blue via-google-red to-google-yellow rounded-full blur opacity-30 group-focus-within:opacity-75 transition duration-500 group-focus-within:duration-200 animate-pulse-slow" />

          <input
            type="text"
            value={input}
            onChange={(e) =>
              setInput(e.target.value)
            }
            placeholder="Ask about your research..."
            disabled={isSending}
            className="relative w-full bg-background border-none rounded-full pl-6 pr-14 py-4 focus:outline-none shadow-sm disabled:opacity-60"
          />

          <button
            type="submit"
            disabled={
              !input.trim() ||
              isSending
            }
            className="absolute right-2 top-1/2 -translate-y-1/2 p-2.5 bg-google-blue hover:bg-google-blue/90 text-white rounded-full transition-colors disabled:opacity-50 shadow-md"
          >
            {isSending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>

        </form>

      </div>
    </div>
  );
}