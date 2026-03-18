import { useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { ChatMessage } from '@/types';
import { AppAvatar, UserAvatar } from '@/components/ui/Avatar';
import { parseMessageWithCitations } from './parseMessageWithCitations';

/** Props for the MessageList component. */
interface MessageListProps {
  /** Array of chat messages to display */
  messages: ChatMessage[];
  /** Whether a response is currently streaming */
  isLoading: boolean;
  /** Callback when a user clicks an inline citation badge */
  onCitationClick?: (index: number) => void;
}

/** Scrollable list of chat messages with Markdown rendering and inline citations. */
export function MessageList({ messages, isLoading, onCitationClick }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center text-gray-400 dark:text-gray-500">
        <div className="text-center animate-fade-in">
          <AppAvatar size="md" />
          <p className="text-sm font-medium text-gray-900 dark:text-gray-200">No messages yet</p>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Ask a question about your documents to get started.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
        {messages.map((message, index) => (
          <MessageRow
            key={index}
            message={message}
            isStreaming={
              isLoading &&
              message.role === 'assistant' &&
              index === messages.length - 1
            }
            onCitationClick={onCitationClick}
          />
        ))}
        {isLoading && messages[messages.length - 1]?.role === 'user' && (
          <div className="flex gap-4 animate-fade-in">
            <AppAvatar size="sm" />
            <div className="pt-1">
              <LoadingDots />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}


/**
 * Recursively walk React children produced by ReactMarkdown and replace
 * citation markers like [1], [2] with clickable CitationLink components.
 */
function renderWithCitations(
  children: React.ReactNode,
  onCitationClick?: (index: number) => void,
): React.ReactNode {
  if (!onCitationClick) return children;

  const process = (node: React.ReactNode): React.ReactNode => {
    if (typeof node === 'string') {
      return parseMessageWithCitations(node, onCitationClick);
    }
    return node;
  };

  if (Array.isArray(children)) {
    return children.flatMap((child, i) => {
      const result = process(child);
      return Array.isArray(result)
        ? result.map((r, j) => (typeof r === 'string' ? r : <span key={`${i}-${j}`}>{r}</span>))
        : [typeof result === 'string' ? result : <span key={i}>{result}</span>];
    });
  }

  const result = process(children);
  return Array.isArray(result) ? result : children;
}

interface MessageRowProps {
  message: ChatMessage;
  isStreaming: boolean;
  onCitationClick?: (index: number) => void;
}

/** Renders a single user or assistant message row with avatar and content. */
function MessageRow({ message, isStreaming, onCitationClick }: MessageRowProps) {
  const isUser = message.role === 'user';

  return (
    <div className="flex gap-4 animate-fade-in">
      {isUser ? <UserAvatar size="sm" /> : <AppAvatar size="sm" />}
      <div className="flex-1 min-w-0 pt-0.5">
        <div className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
          {isUser ? 'You' : 'doc-qna'}
        </div>
        {isUser ? (
          <p className="text-sm text-gray-900 dark:text-gray-100 whitespace-pre-wrap leading-relaxed">
            {message.content}
          </p>
        ) : (
          <div className="prose prose-sm dark:prose-invert max-w-none text-gray-900 dark:text-gray-100 leading-relaxed [&_pre]:bg-[#1e1e1e] [&_pre]:rounded-lg [&_pre]:p-3 [&_pre]:text-gray-100 [&_code:not(pre_code)]:rounded [&_code:not(pre_code)]:bg-gray-100 [&_code:not(pre_code)]:dark:bg-white/10 [&_code:not(pre_code)]:px-1.5 [&_code:not(pre_code)]:py-0.5 [&_code:not(pre_code)]:text-sm [&_code:not(pre_code)]:font-mono">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                p({ children }) {
                  return <p>{renderWithCitations(children, onCitationClick)}</p>;
                },
                li({ children }) {
                  return <li>{renderWithCitations(children, onCitationClick)}</li>;
                },
              }}
            >
              {message.content}
            </ReactMarkdown>
            {isStreaming && (
              <span className="inline-block w-1.5 h-4 bg-gray-900 dark:bg-gray-100 animate-blink ml-0.5 align-text-bottom rounded-sm" />
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/** Animated bouncing dots shown while waiting for the assistant response. */
function LoadingDots() {
  return (
    <div className="flex items-center space-x-1.5 py-1">
      <span className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce [animation-delay:0ms]" />
      <span className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce [animation-delay:150ms]" />
      <span className="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce [animation-delay:300ms]" />
    </div>
  );
}
