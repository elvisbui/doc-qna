import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { useChat } from '@/hooks/useChat';
import { useKeyboardShortcut } from '@/hooks/useKeyboardShortcut';
import { useDocuments } from '@/hooks/useDocuments';
import { MessageList } from '@/components/chat/MessageList';
import { ChatInput } from '@/components/chat/ChatInput';
import { CitationPanel } from '@/components/chat/CitationPanel';
import { PluginActivityPanel } from '@/components/chat/PluginActivityPanel';
import { ConversationSummary } from '@/components/chat/ConversationSummary';
import { exportAsMarkdown, exportAsJSON, downloadFile } from '@/lib/exportChat';
import type { ChatMessage, Citation } from '@/types';

const DEFAULT_STARTERS = [
  'Summarize the main points',
  'What topics are covered?',
  'Find information about…',
  'Compare the documents',
];

interface ChatPageProps {
  initialQuery?: string | null;
  onQueryConsumed?: () => void;
  conversationId?: string | null;
  initialMessages?: ChatMessage[];
  initialCitations?: Citation[];
  onMessagesChange?: (messages: ChatMessage[], citations: Citation[]) => void;
}

export function ChatPage({
  initialQuery,
  onQueryConsumed,
  conversationId,
  initialMessages,
  initialCitations,
  onMessagesChange,
}: ChatPageProps) {
  const { documents, refresh: refreshDocuments } = useDocuments();
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);
  const [highlightedCitation, setHighlightedCitation] = useState<number | null>(null);
  const highlightTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleCitationClick = useCallback((index: number) => {
    if (highlightTimerRef.current) {
      clearTimeout(highlightTimerRef.current);
    }
    setHighlightedCitation(index);
    const HIGHLIGHT_DURATION_MS = 3000;
    highlightTimerRef.current = setTimeout(() => {
      setHighlightedCitation(null);
      highlightTimerRef.current = null;
    }, HIGHLIGHT_DURATION_MS);
  }, []);

  useEffect(() => {
    return () => {
      if (highlightTimerRef.current) {
        clearTimeout(highlightTimerRef.current);
      }
    };
  }, []);

  useEffect(() => {
    refreshDocuments();
  }, [refreshDocuments]);

  const readyDocuments = useMemo(
    () => documents.filter((d) => d.status === 'ready'),
    [documents],
  );

  const chatOptions = useMemo(
    () => ({
      documentIds: selectedDocIds.length > 0 ? selectedDocIds : undefined,
      initialMessages,
      initialCitations,
      onMessagesChange,
    }),
    [selectedDocIds, initialMessages, initialCitations, onMessagesChange],
  );

  const {
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
  } = useChat(chatOptions);

  const prevConvIdRef = useRef(conversationId);
  useEffect(() => {
    if (conversationId !== prevConvIdRef.current) {
      prevConvIdRef.current = conversationId;
      resetWith(initialMessages ?? [], initialCitations ?? []);
    }
  }, [conversationId, initialMessages, initialCitations, resetWith]);

  useEffect(() => {
    if (initialQuery && !isLoading) {
      sendMessage(initialQuery);
      onQueryConsumed?.();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialQuery]);

  useKeyboardShortcut({ key: 'Escape' }, cancelStream, isLoading);

  const timestamp = () => new Date().toISOString().replace(/[:.]/g, '-');

  const handleExportMarkdown = useCallback(() => {
    const content = exportAsMarkdown(messages);
    downloadFile(content, `chat-${timestamp()}.md`, 'text/markdown');
  }, [messages]);

  const handleExportJSON = useCallback(() => {
    const content = exportAsJSON(messages);
    downloadFile(content, `chat-${timestamp()}.json`, 'application/json');
  }, [messages]);

  const toggleDocId = (id: string) => {
    setSelectedDocIds((prev) =>
      prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id],
    );
  };

  const hasMessages = messages.length > 0;

  return (
    <div className="flex flex-col flex-1 min-h-0 bg-white dark:bg-[#212121]">
      {(readyDocuments.length > 0 || hasMessages) && (
        <div className="flex-shrink-0 flex items-center justify-between gap-2 px-4 py-2 border-b border-gray-200 dark:border-white/10">
          <div className="flex items-center gap-2 flex-wrap min-w-0">
            {readyDocuments.length > 0 && (
              <>
                {readyDocuments.map((doc) => (
                  <button
                    key={doc.id}
                    onClick={() => toggleDocId(doc.id)}
                    className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs transition-colors ${
                      selectedDocIds.includes(doc.id)
                        ? 'bg-gray-900 dark:bg-white text-white dark:text-gray-900'
                        : 'bg-gray-100 dark:bg-white/5 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-white/10'
                    }`}
                  >
                    {doc.filename}
                    {selectedDocIds.includes(doc.id) && (
                      <svg className="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                    )}
                  </button>
                ))}
                {selectedDocIds.length > 0 && (
                  <button
                    onClick={() => setSelectedDocIds([])}
                    className="text-xs text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
                  >
                    Clear
                  </button>
                )}
              </>
            )}
          </div>

          <div className="flex items-center gap-1 flex-shrink-0">
            {isLoading && (
              <button
                onClick={cancelStream}
                className="rounded-full px-3 py-1 text-xs text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-white/10 transition-colors"
              >
                Stop
              </button>
            )}
            {hasMessages && (
              <>
                <button
                  onClick={handleExportMarkdown}
                  className="p-1.5 rounded-lg text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-white/5 transition-colors"
                  title="Export as Markdown"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
                  </svg>
                </button>
                <button
                  onClick={handleExportJSON}
                  className="p-1.5 rounded-lg text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-white/5 transition-colors"
                  title="Export as JSON"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M17.25 6.75L22.5 12l-5.25 5.25m-10.5 0L1.5 12l5.25-5.25m7.5-3l-4.5 16.5" />
                  </svg>
                </button>
                <button
                  onClick={clearMessages}
                  className="p-1.5 rounded-lg text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-100 dark:hover:bg-white/5 transition-colors"
                  title="Clear chat"
                >
                  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                  </svg>
                </button>
              </>
            )}
          </div>
        </div>
      )}

      <div className="flex-1 flex flex-col min-h-0">
        {conversationSummary && (
          <ConversationSummary summary={conversationSummary} />
        )}

        {!hasMessages ? (
          <div className="flex-1 flex flex-col items-center justify-center px-4">
            <div className="text-center mb-8 animate-fade-in">
              <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100">
                Start a new chat
              </h2>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                Ask something about your uploaded documents.
              </p>
            </div>

            {DEFAULT_STARTERS.length > 0 && (
              <div className="w-full max-w-2xl mx-auto flex flex-wrap justify-center gap-2 animate-slide-up">
                {DEFAULT_STARTERS.slice(0, 4).map((query) => (
                  <button
                    key={query}
                    onClick={() => sendMessage(query)}
                    className="rounded-full border border-gray-200 dark:border-white/15 px-3.5 py-1.5 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-white/5 transition-colors"
                  >
                    {query}
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          <>
            <MessageList messages={messages} isLoading={isLoading} onCitationClick={handleCitationClick} />

            {error && (
              <div className="max-w-3xl mx-auto w-full px-4 pb-2">
                <p className="text-sm text-gray-700 dark:text-gray-300">{error}</p>
              </div>
            )}

            <CitationPanel citations={citations} highlightedIndex={highlightedCitation} />
            <PluginActivityPanel trace={pluginTrace} />
          </>
        )}

        <div className="flex-shrink-0">
          <ChatInput onSend={sendMessage} isLoading={isLoading} />
        </div>
      </div>
    </div>
  );
}
