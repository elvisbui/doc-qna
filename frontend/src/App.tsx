import { useState, useCallback, useRef } from 'react';
import { LandingPage } from '@/pages/LandingPage';
import { DocumentsPage } from '@/pages/DocumentsPage';
import { ChatPage } from '@/pages/ChatPage';
import { SettingsPage } from '@/pages/SettingsPage';
import { PluginsPage } from '@/pages/PluginsPage';
import { PacksPage } from '@/pages/PacksPage';
import { MetricsPage } from '@/pages/MetricsPage';
import { ToastContainer } from '@/components/ui/Toast';
import { useToast } from '@/hooks/useToast';
import { useDarkMode } from '@/hooks/useDarkMode';
import { useConversations } from '@/hooks/useConversations';
import type { ChatMessage, Citation } from '@/types';

type Tab = 'home' | 'documents' | 'chat' | 'packs' | 'plugins' | 'metrics' | 'settings';

const IS_DEMO = import.meta.env.VITE_DEMO_MODE === 'true';

const ALL_NAV_ITEMS: { id: Tab; label: string; hideInDemo?: boolean }[] = [
  { id: 'chat', label: 'Chat' },
  { id: 'documents', label: 'Documents' },
  { id: 'packs', label: 'Packs' },
  { id: 'plugins', label: 'Plugins' },
  { id: 'metrics', label: 'Metrics', hideInDemo: true },
  { id: 'settings', label: 'Settings', hideInDemo: true },
];

const NAV_ITEMS = IS_DEMO ? ALL_NAV_ITEMS.filter((item) => !item.hideInDemo) : ALL_NAV_ITEMS;

export function App() {
  const [activeTab, setActiveTab] = useState<Tab>('home');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const pendingQueryRef = useRef<string | null>(null);
  const { toasts, addToast, removeToast } = useToast();
  const { isDark, toggle } = useDarkMode();

  const {
    conversations,
    activeId,
    activeConversation,
    createConversation,
    updateConversation,
    deleteConversation,
    selectConversation,
    clearActive,
  } = useConversations();

  const handleNewChat = useCallback(() => {
    createConversation();
    setActiveTab('chat');
    setSidebarOpen(false);
  }, [createConversation]);

  const handleNavigateToChat = useCallback((query: string) => {
    createConversation();
    pendingQueryRef.current = query;
    setActiveTab('chat');
  }, [createConversation]);

  const handleSelectConversation = useCallback((id: string) => {
    selectConversation(id);
    setActiveTab('chat');
    setSidebarOpen(false);
  }, [selectConversation]);

  const handleDeleteConversation = useCallback((e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    deleteConversation(id);
  }, [deleteConversation]);

  const handleMessagesChange = useCallback((messages: ChatMessage[], citations: Citation[]) => {
    if (activeId) {
      updateConversation(activeId, messages, citations);
    }
  }, [activeId, updateConversation]);

  const handleTabClick = useCallback((tab: Tab) => {
    if (tab === 'chat') {
      handleNewChat();
      return;
    }
    setActiveTab(tab);
    setSidebarOpen(false);
  }, [handleNewChat]);

  const handleLogoClick = useCallback(() => {
    clearActive();
    setActiveTab('home');
    setSidebarOpen(false);
  }, [clearActive]);

  const ensureConversation = useCallback(() => {
    if (activeTab === 'chat' && !activeId) {
      createConversation();
    }
  }, [activeTab, activeId, createConversation]);

  if (activeTab === 'chat' && !activeId) {
    ensureConversation();
  }

  return (
    <div className="h-screen flex bg-white dark:bg-[#212121] transition-colors duration-200">
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/40 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <aside
        className={`fixed md:relative z-50 flex flex-col h-full w-[260px] bg-[#f9f9f9] dark:bg-[#171717] sidebar-transition ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
      >
        <div className="flex items-center justify-between p-3">
          <button
            onClick={handleLogoClick}
            className="flex items-center gap-2 px-2 py-1 rounded-lg hover:bg-gray-200/60 dark:hover:bg-white/5 transition-colors"
          >
            <span className="text-sm font-semibold text-gray-900 dark:text-gray-100">
              doc-qna
            </span>
          </button>
          <button
            onClick={handleNewChat}
            className="p-1.5 rounded-lg text-gray-500 dark:text-gray-400 hover:bg-gray-200/60 dark:hover:bg-white/10 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
            title="New chat"
            aria-label="New chat"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0115.75 21H5.25A2.25 2.25 0 013 18.75V8.25A2.25 2.25 0 015.25 6H10" />
            </svg>
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-2 py-1">
          <nav className="space-y-0.5">
            {NAV_ITEMS.map((item) => (
              <button
                key={item.id}
                onClick={() => handleTabClick(item.id)}
                className={`w-full flex items-center px-3 py-2 rounded-lg text-sm transition-colors ${
                  activeTab === item.id
                    ? 'bg-gray-200/70 dark:bg-white/10 text-gray-900 dark:text-gray-100'
                    : 'text-gray-700 dark:text-gray-300 hover:bg-gray-200/50 dark:hover:bg-white/5'
                }`}
              >
                {item.label}
              </button>
            ))}
          </nav>

          {conversations.length > 0 && (
            <div className="mt-6">
              <div className="px-3 py-1 text-xs text-gray-500 dark:text-gray-500">
                Chats
              </div>
              <div className="space-y-0.5">
                {conversations.map((conv) => (
                  <div
                    key={conv.id}
                    onClick={() => handleSelectConversation(conv.id)}
                    className={`group flex items-center gap-2 px-3 py-2 rounded-lg text-sm cursor-pointer transition-colors ${
                      activeId === conv.id && activeTab === 'chat'
                        ? 'bg-gray-200/70 dark:bg-white/10 text-gray-900 dark:text-gray-100'
                        : 'text-gray-700 dark:text-gray-300 hover:bg-gray-200/50 dark:hover:bg-white/5'
                    }`}
                  >
                    <span className="flex-1 truncate">{conv.title}</span>
                    <button
                      onClick={(e) => handleDeleteConversation(e, conv.id)}
                      className="hidden group-hover:block p-0.5 rounded text-gray-400 dark:text-gray-500 hover:text-gray-900 dark:hover:text-gray-100 transition-colors"
                      title="Delete chat"
                      aria-label="Delete chat"
                    >
                      <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
                      </svg>
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="p-3 border-t border-gray-200/60 dark:border-white/10">
          <button
            onClick={toggle}
            className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-200/50 dark:hover:bg-white/5 transition-colors"
          >
            {isDark ? (
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z" />
              </svg>
            ) : (
              <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M21.752 15.002A9.718 9.718 0 0118 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 003 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 009.002-5.998z" />
              </svg>
            )}
            {isDark ? 'Light' : 'Dark'}
          </button>
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <div className="md:hidden flex items-center h-12 px-3 border-b border-gray-200 dark:border-white/10 bg-white dark:bg-[#212121]">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-1.5 -ml-1 rounded-lg text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-white/10"
            aria-label="Open menu"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          <span className="ml-3 text-sm font-medium text-gray-900 dark:text-gray-100">
            {activeTab === 'chat'
              ? (activeConversation?.title ?? 'New chat')
              : (NAV_ITEMS.find(n => n.id === activeTab)?.label ?? 'doc-qna')}
          </span>
        </div>

        <main className="flex-1 min-h-0 flex flex-col">
          <div className={`flex-1 min-h-0 overflow-y-auto ${activeTab === 'home' ? '' : 'hidden'}`}>
            <LandingPage onNavigateToChat={handleNavigateToChat} onNavigateToDocuments={() => setActiveTab('documents')} />
          </div>
          <div className={`flex-1 min-h-0 overflow-y-auto ${activeTab === 'documents' ? '' : 'hidden'}`}>
            <DocumentsPage addToast={addToast} isActive={activeTab === 'documents'} />
          </div>
          <div className={`flex-1 min-h-0 flex flex-col ${activeTab === 'chat' ? '' : 'hidden'}`}>
            <ChatPage
              key={activeId ?? 'empty'}
              conversationId={activeId}
              initialQuery={pendingQueryRef.current}
              onQueryConsumed={() => { pendingQueryRef.current = null; }}
              initialMessages={activeConversation?.messages}
              initialCitations={activeConversation?.citations}
              onMessagesChange={handleMessagesChange}
            />
          </div>
          <div className={`flex-1 min-h-0 overflow-y-auto ${activeTab === 'packs' ? '' : 'hidden'}`}>
            <PacksPage />
          </div>
          <div className={`flex-1 min-h-0 overflow-y-auto ${activeTab === 'plugins' ? '' : 'hidden'}`}>
            <PluginsPage />
          </div>
          {!IS_DEMO && (
            <div className={`flex-1 min-h-0 overflow-y-auto ${activeTab === 'metrics' ? '' : 'hidden'}`}>
              <MetricsPage />
            </div>
          )}
          {!IS_DEMO && (
            <div className={`flex-1 min-h-0 overflow-y-auto ${activeTab === 'settings' ? '' : 'hidden'}`}>
              <SettingsPage addToast={addToast} />
            </div>
          )}
        </main>
      </div>

      <ToastContainer toasts={toasts} onClose={removeToast} />
    </div>
  );
}
