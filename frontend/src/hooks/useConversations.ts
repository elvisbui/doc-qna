import { useState, useCallback, useEffect } from 'react';
import type { ChatMessage, Citation } from '@/types';

const STORAGE_KEY = 'doc-qna-conversations';
const MAX_CONVERSATIONS = 50;

/** A saved chat conversation with its messages and metadata. */
export interface Conversation {
  /** Unique identifier for the conversation. */
  id: string;
  /** Display title derived from the first user message. */
  title: string;
  /** Ordered list of messages in the conversation. */
  messages: ChatMessage[];
  /** Citations from the most recent assistant response. */
  citations: Citation[];
  /** ISO 8601 timestamp of when the conversation was created. */
  createdAt: string;
  /** ISO 8601 timestamp of the last update. */
  updatedAt: string;
}

/**
 * Generates a unique conversation ID using timestamp and random suffix.
 * @returns A unique string identifier.
 */
function generateId(): string {
  return `conv-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

/**
 * Loads saved conversations from localStorage.
 * @returns Array of conversations, or empty array if none found or on error.
 */
function loadConversations(): Conversation[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as Conversation[];
  } catch {
    return [];
  }
}

/**
 * Persists conversations to localStorage, capped at MAX_CONVERSATIONS.
 * @param conversations - The conversations array to save.
 */
function saveConversations(conversations: Conversation[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations.slice(0, MAX_CONVERSATIONS)));
  } catch {
    // localStorage full or unavailable
  }
}

/**
 * Derives a conversation title from the first user message, truncated to 50 characters.
 * @param messages - The conversation's message history.
 * @returns A title string, or "New chat" if no user messages exist.
 */
function deriveTitle(messages: ChatMessage[]): string {
  const firstUser = messages.find((m) => m.role === 'user');
  if (!firstUser) return 'New chat';
  const text = firstUser.content.trim();
  return text.length > 50 ? text.slice(0, 50) + '...' : text;
}

/**
 * Manages conversation CRUD operations with localStorage persistence.
 * @returns Conversation list, active conversation state, and action methods.
 */
export function useConversations() {
  const [conversations, setConversations] = useState<Conversation[]>(loadConversations);
  const [activeId, setActiveId] = useState<string | null>(null);

  // Persist on change
  useEffect(() => {
    saveConversations(conversations);
  }, [conversations]);

  const activeConversation = conversations.find((c) => c.id === activeId) ?? null;

  const createConversation = useCallback((): string => {
    const id = generateId();
    const now = new Date().toISOString();
    const conv: Conversation = {
      id,
      title: 'New chat',
      messages: [],
      citations: [],
      createdAt: now,
      updatedAt: now,
    };
    setConversations((prev) => [conv, ...prev]);
    setActiveId(id);
    return id;
  }, []);

  const updateConversation = useCallback(
    (id: string, messages: ChatMessage[], citations: Citation[]) => {
      setConversations((prev) =>
        prev.map((c) =>
          c.id === id
            ? {
                ...c,
                messages,
                citations,
                title: deriveTitle(messages),
                updatedAt: new Date().toISOString(),
              }
            : c,
        ),
      );
    },
    [],
  );

  const deleteConversation = useCallback(
    (id: string) => {
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (activeId === id) {
        setActiveId(null);
      }
    },
    [activeId],
  );

  const selectConversation = useCallback((id: string) => {
    setActiveId(id);
  }, []);

  const clearActive = useCallback(() => {
    setActiveId(null);
  }, []);

  return {
    conversations,
    activeId,
    activeConversation,
    createConversation,
    updateConversation,
    deleteConversation,
    selectConversation,
    clearActive,
  };
}
