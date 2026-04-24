import { useState, useCallback, useRef, useEffect } from 'react';
import { parseSSEStream } from '@/lib/sse';
import type { SSEEvent } from '@/lib/sse';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

async function* streamChat(
  apiUrl: string,
  query: string,
  signal: AbortSignal,
  history: { role: string; content: string }[],
  apiKey?: string,
): AsyncGenerator<SSEEvent, void, unknown> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'text/event-stream',
  };
  if (apiKey) {
    headers['Authorization'] = `Bearer ${apiKey}`;
  }

  const response = await fetch(`${apiUrl}/api/chat`, {
    method: 'POST',
    headers,
    body: JSON.stringify({ query, history }),
    signal,
  });

  if (!response.ok) {
    const body = await response.text();
    throw new Error(body || response.statusText);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('Response body is not readable');
  }

  yield* parseSSEStream(reader);
}

interface WidgetProps {
  apiUrl: string;
  apiKey?: string;
}

export function Widget({ apiUrl, apiKey }: WidgetProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const messagesRef = useRef<Message[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (isOpen) {
      inputRef.current?.focus();
    }
  }, [isOpen]);

  // Abort in-flight request on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const sendMessage = useCallback(async () => {
    const query = input.trim();
    if (!query || isLoading) return;

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    const history = messagesRef.current.map((m) => ({
      role: m.role,
      content: m.content,
    }));

    const userMessage: Message = { role: 'user', content: query };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setError(null);

    let fullContent = '';

    try {
      setMessages((prev) => [...prev, { role: 'assistant', content: '' }]);

      for await (const { event, data } of streamChat(apiUrl, query, controller.signal, history, apiKey)) {
        switch (event) {
          case 'token':
            fullContent += data;
            setMessages((prev) => {
              const updated = [...prev];
              updated[updated.length - 1] = { role: 'assistant', content: fullContent };
              return updated;
            });
            break;
          case 'error':
            setError(data);
            break;
          case 'done':
            break;
        }
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') return;
      const message = err instanceof Error ? err.message : 'Failed to send message';
      setError(message);
      if (!fullContent) {
        setMessages((prev) => prev.slice(0, -1));
      }
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null;
        setIsLoading(false);
      }
    }
  }, [input, isLoading, apiUrl, apiKey]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
      }
    },
    [sendMessage],
  );

  const handleInputChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    const textarea = e.target;
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
  }, []);

  return (
    <>
      {isOpen && (
        <div className="chat-panel" data-testid="chat-panel">
          <div className="chat-header">
            <span className="chat-header-title">doc-qna</span>
            <button
              className="close-button"
              onClick={() => setIsOpen(false)}
              aria-label="Close chat"
              data-testid="close-button"
            >
              <svg viewBox="0 0 24 24">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>
          </div>

          {messages.length === 0 ? (
            <div className="message-list-empty">
              Ask a question about your documents.
            </div>
          ) : (
            <div className="message-list">
              {messages.map((msg, i) => (
                <div
                  key={i}
                  className={`message ${msg.role === 'user' ? 'message-user' : 'message-assistant'}`}
                >
                  {msg.content}
                  {isLoading && msg.role === 'assistant' && i === messages.length - 1 && (
                    <span className="streaming-cursor" />
                  )}
                </div>
              ))}
              {isLoading && messages[messages.length - 1]?.role === 'user' && (
                <div className="message message-assistant">
                  <div className="loading-dots">
                    <span />
                    <span />
                    <span />
                  </div>
                </div>
              )}
              {error && (
                <div className="message message-error">{error}</div>
              )}
              <div ref={bottomRef} />
            </div>
          )}

          <div className="chat-input-area">
            <textarea
              ref={inputRef}
              className="chat-input"
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder="Message"
              rows={1}
              disabled={isLoading}
              data-testid="chat-input"
            />
            <button
              className="send-button"
              onClick={sendMessage}
              disabled={isLoading || !input.trim()}
              data-testid="send-button"
            >
              Send
            </button>
          </div>
        </div>
      )}

      <button
        className="widget-button"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-label="Open chat"
        data-testid="widget-button"
      >
        <svg viewBox="0 0 24 24">
          {isOpen ? (
            <path d="M18 6L6 18M6 6l12 12" />
          ) : (
            <path d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.087.16 2.185.283 3.293.369V21l4.076-4.076a1.526 1.526 0 011.037-.443 48.282 48.282 0 005.68-.494c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0012 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018z" />
          )}
        </svg>
      </button>
    </>
  );
}
