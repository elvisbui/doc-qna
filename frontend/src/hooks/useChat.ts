import { useState, useCallback, useRef, useEffect } from 'react';
import type { ChatMessage, Citation, PluginTraceEntry } from '@/types';
import { streamChatMessage } from '@/lib/api';

/** Options for configuring the useChat hook. */
interface UseChatOptions {
  /** Document IDs to scope the chat query to specific documents. */
  documentIds?: string[];
  /** Pre-existing messages to initialize the chat with. */
  initialMessages?: ChatMessage[];
  /** Pre-existing citations to initialize the chat with. */
  initialCitations?: Citation[];
  /** Callback invoked whenever messages or citations change (used for persistence). */
  onMessagesChange?: (messages: ChatMessage[], citations: Citation[]) => void;
}

/** Return value of the useChat hook. */
interface UseChatReturn {
  /** Current list of chat messages in the conversation. */
  messages: ChatMessage[];
  /** Citations returned by the most recent assistant response. */
  citations: Citation[];
  /** Plugin execution trace entries from the most recent response. */
  pluginTrace: PluginTraceEntry[];
  /** LLM-generated summary of older conversation history, if any. */
  conversationSummary: string | null;
  /** Whether a streaming response is currently in progress. */
  isLoading: boolean;
  /** Error message from the most recent failed request, if any. */
  error: string | null;
  /** Send a user query and stream the assistant's response. */
  sendMessage: (query: string) => Promise<void>;
  /** Clear all messages, citations, and error state. */
  clearMessages: () => void;
  /** Abort the currently streaming response. */
  cancelStream: () => void;
  /** Replace all messages and citations (used when switching conversations). */
  resetWith: (messages: ChatMessage[], citations: Citation[]) => void;
}

/**
 * Manages chat state including messages, citations, and streaming SSE responses.
 * @param options - Configuration options for the chat session.
 * @returns Chat state and action methods.
 */
export function useChat(options: UseChatOptions = {}): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>(options.initialMessages ?? []);
  const [citations, setCitations] = useState<Citation[]>(options.initialCitations ?? []);
  const [pluginTrace, setPluginTrace] = useState<PluginTraceEntry[]>([]);
  const [conversationSummary, setConversationSummary] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const messagesRef = useRef<ChatMessage[]>(options.initialMessages ?? []);
  const onMessagesChangeRef = useRef(options.onMessagesChange);

  // Keep refs in sync
  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  useEffect(() => {
    onMessagesChangeRef.current = options.onMessagesChange;
  }, [options.onMessagesChange]);

  // Notify parent of message changes (for persistence)
  useEffect(() => {
    if (messages.length > 0) {
      onMessagesChangeRef.current?.(messages, citations);
    }
  }, [messages, citations]);

  const resetWith = useCallback((newMessages: ChatMessage[], newCitations: Citation[]) => {
    setMessages(newMessages);
    setCitations(newCitations);
    setPluginTrace([]);
    setConversationSummary(null);
    setError(null);
    messagesRef.current = newMessages;
  }, []);

  const cancelStream = useCallback(() => {
    abortControllerRef.current?.abort();
    abortControllerRef.current = null;
  }, []);

  const sendMessage = useCallback(async (query: string) => {
    const updateLastMessage = (content: string) => {
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1] = { role: 'assistant', content };
        return updated;
      });
    };
    cancelStream();
    const controller = new AbortController();
    abortControllerRef.current = controller;

    const userMessage: ChatMessage = { role: 'user', content: query };

    // Capture current messages for history before updating state
    const currentMessages = messagesRef.current;
    const history = currentMessages.map((m) => ({
      role: m.role,
      content: m.content,
    }));

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);
    setCitations([]);
    setPluginTrace([]);

    let fullContent = '';

    try {
      setMessages((prev) => [...prev, { role: 'assistant', content: '' }]);

      for await (const { event, data } of streamChatMessage(query, controller.signal, history, options.documentIds)) {
        switch (event) {
          case 'token':
            fullContent += data;
            updateLastMessage(fullContent);
            break;
          case 'citations': {
            const parsed = JSON.parse(data) as Citation[];
            setCitations(parsed);
            break;
          }
          case 'plugin_trace': {
            const parsed = JSON.parse(data) as PluginTraceEntry[];
            setPluginTrace(parsed);
            break;
          }
          case 'summary': {
            const parsed = JSON.parse(data) as { summary: string };
            setConversationSummary(parsed.summary);
            break;
          }
          case 'done':
            break;
          case 'error':
            setError(data);
            break;
        }
      }
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') return;
      const message =
        err instanceof Error ? err.message : 'Failed to send message';
      setError(message);

      if (!fullContent) {
        setMessages((prev) => prev.slice(0, -1));
      }
    } finally {
      if (abortControllerRef.current === controller) {
        abortControllerRef.current = null;
        setIsLoading(false);
      }
    }
  }, [cancelStream, options.documentIds]);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setCitations([]);
    setPluginTrace([]);
    setConversationSummary(null);
    setError(null);
  }, []);

  return {
    messages,
    citations,
    pluginTrace,
    conversationSummary,
    isLoading,
    error,
    sendMessage,
    clearMessages,
    cancelStream,
    resetWith,
  };
}
