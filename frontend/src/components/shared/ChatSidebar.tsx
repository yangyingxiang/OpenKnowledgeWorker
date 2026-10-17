'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { api, ChatSession, ChatMessage, KnowledgeItem, Question } from '@/lib/api';
import { useSSE } from '@/lib/useSSE';
import { Send, MessageSquare, Lightbulb, HelpCircle, Plus } from 'lucide-react';
import * as Tabs from '@radix-ui/react-tabs';
import { ChatMessages } from '@/components/chat/ChatMessages';
import { KnowledgeList } from '@/components/chat/KnowledgeList';
import { QuestionList } from '@/components/chat/QuestionList';

/* ─── Props ──────────────────────────────────────────────────── */

export interface ChatSidebarProps {
  processId: string;
  /** Page context sent to the backend so the agent can use page-specific tools. */
  context?: 'sop' | 'code' | 'tests';
  /** Optional callback fired after chat SSE events (e.g., to refresh PDD). */
  onChatEvent?: (event: Record<string, unknown>) => void;
  /** When set, the sidebar will auto-send this message (creating a session if needed). */
  pendingMessage?: string | null;
  /** Callback to clear the pending message after it has been sent. */
  onPendingMessageSent?: () => void;
}

/* ─── Component ──────────────────────────────────────────────── */

export function ChatSidebar({
  processId,
  context,
  onChatEvent,
  pendingMessage,
  onPendingMessageSent,
}: ChatSidebarProps) {
  // Chat state
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSession, setActiveSession] = useState<ChatSession | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState('');

  // Knowledge & Questions
  const [knowledge, setKnowledge] = useState<KnowledgeItem[]>([]);
  const [questions, setQuestions] = useState<Question[]>([]);

  const chat = useSSE();
  const chatEndRef = useRef<HTMLDivElement>(null);
  const [activeTab, setActiveTab] = useState('chat');

  // Loaders
  const loadSessions = useCallback(async () => {
    try {
      setSessions(await api.listChatSessions(processId));
    } catch {}
  }, [processId]);

  const loadKnowledge = useCallback(async () => {
    try {
      setKnowledge(await api.listKnowledge(processId));
    } catch {}
  }, [processId]);

  const loadQuestions = useCallback(async () => {
    try {
      setQuestions(await api.listQuestions(processId));
    } catch {}
  }, [processId]);

  useEffect(() => {
    loadSessions();
    loadKnowledge();
    loadQuestions();
  }, [loadSessions, loadKnowledge, loadQuestions]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, chat.streamText]);

  // Auto-send pending message from parent
  useEffect(() => {
    if (!pendingMessage || chat.isStreaming) return;

    const sendPending = async () => {
      let session = activeSession;

      // Create a new session if none is active
      if (!session) {
        try {
          session = await api.createChatSession(processId, {
            expert_name: 'Domain Expert',
            expert_role: 'SME',
          });
          setSessions((prev) => [session!, ...prev]);
          setActiveSession(session);
          setMessages(session.messages || []);
        } catch (err) {
          console.error('Failed to create session for pending message:', err);
          return;
        }
      }

      const content = pendingMessage.trim();
      if (!content) return;

      // Add optimistic user message
      setMessages((prev) => [
        ...prev,
        {
          id: `temp-${Date.now()}`,
          session_id: session!.id,
          role: 'user',
          content,
          created_at: new Date().toISOString(),
        },
      ]);

      // Send via SSE (mirrors handleSendMessage logic)
      chat.setStreamText('');
      chat.startStream(
        () => api.sendMessage(processId, session!.id, content, context),
        (event) => {
          onChatEvent?.(event as Record<string, unknown>);

          if (event.type === 'tool_result' && event.name === 'resolve_question') {
            loadQuestions();
          }
          if (event.type === 'tool_result' && event.name === 'write_to_knowledge') {
            loadKnowledge();
          }
          if (event.type === 'tool_result' && event.name === 'create_question') {
            loadQuestions();
          }
          if (event.type === 'done') {
            const text = (event.text as string) || '';
            if (text) {
              setMessages((prev) => [
                ...prev,
                {
                  id: `assistant-${Date.now()}`,
                  session_id: session!.id,
                  role: 'assistant',
                  content: text,
                  created_at: new Date().toISOString(),
                },
              ]);
              chat.setStreamText('');
            }
            loadKnowledge();
            loadQuestions();
          }
        },
      );

      // Notify parent so it can clear the pending message
      onPendingMessageSent?.();
      // Switch to the chat tab
      setActiveTab('chat');
    };

    sendPending();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingMessage]);

  // Session management
  const handleNewSession = async () => {
    try {
      const session = await api.createChatSession(processId, {
        expert_name: 'Domain Expert',
        expert_role: 'SME',
      });
      setSessions((prev) => [session, ...prev]);
      setActiveSession(session);
      setMessages(session.messages || []);
    } catch (err) {
      console.error('Failed to create session:', err);
    }
  };

  const handleSelectSession = async (session: ChatSession) => {
    try {
      const full = await api.getChatSession(processId, session.id);
      setActiveSession(full);
      setMessages(full.messages || []);
    } catch (err) {
      console.error('Failed to load session:', err);
    }
  };

  const handleSendMessage = async () => {
    if (!chatInput.trim() || !activeSession || chat.isStreaming) return;
    const content = chatInput.trim();
    setChatInput('');

    setMessages((prev) => [
      ...prev,
      {
        id: `temp-${Date.now()}`,
        session_id: activeSession.id,
        role: 'user',
        content,
        created_at: new Date().toISOString(),
      },
    ]);

    chat.setStreamText('');
    chat.startStream(
      () => api.sendMessage(processId, activeSession.id, content, context),
      (event) => {
        // Forward events to parent
        onChatEvent?.(event as Record<string, unknown>);

        // Track side effects
        if (event.type === 'tool_result' && event.name === 'resolve_question') {
          loadQuestions();
        }
        if (event.type === 'tool_result' && event.name === 'write_to_knowledge') {
          loadKnowledge();
        }
        if (event.type === 'tool_result' && event.name === 'create_question') {
          loadQuestions();
        }
        if (event.type === 'done') {
          const text = (event.text as string) || '';
          if (text) {
            setMessages((prev) => [
              ...prev,
              {
                id: `assistant-${Date.now()}`,
                session_id: activeSession.id,
                role: 'assistant',
                content: text,
                created_at: new Date().toISOString(),
              },
            ]);
            chat.setStreamText('');
          }
          loadKnowledge();
          loadQuestions();
        }
      },
    );
  };

  return (
    <div className="w-[380px] border-l border-[var(--okw-border)] bg-white flex flex-col shrink-0">
      <Tabs.Root
        value={activeTab}
        onValueChange={setActiveTab}
        className="flex-1 flex flex-col overflow-hidden"
      >
        <Tabs.List className="flex border-b border-[var(--okw-border)] shrink-0">
          {[
            { value: 'chat', label: 'Chat', icon: MessageSquare, count: messages.length },
            { value: 'knowledge', label: 'Knowledge', icon: Lightbulb, count: knowledge.length },
            {
              value: 'questions',
              label: 'Questions',
              icon: HelpCircle,
              count: questions.filter((q) => q.status === 'OPEN').length,
            },
          ].map((tab) => (
            <Tabs.Trigger
              key={tab.value}
              value={tab.value}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs font-medium border-b-2 transition-colors ${
                activeTab === tab.value
                  ? 'border-[var(--okw-primary)] text-[var(--okw-primary)]'
                  : 'border-transparent text-[var(--okw-text-muted)] hover:text-[var(--okw-text)]'
              }`}
            >
              <tab.icon size={14} />
              {tab.label}
              {tab.count > 0 && (
                <span className="ml-1 px-1.5 py-0.5 rounded-full bg-[var(--okw-bg)] text-[10px]">
                  {tab.count}
                </span>
              )}
            </Tabs.Trigger>
          ))}
        </Tabs.List>

        {/* Chat tab */}
        <Tabs.Content value="chat" className="flex-1 flex flex-col overflow-hidden min-h-0">
          {/* Session selector */}
          <div className="px-3 py-2 border-b border-[var(--okw-border)] flex items-center gap-2">
            <select
              className="flex-1 text-xs bg-[var(--okw-bg)] border border-[var(--okw-border)] rounded px-2 py-1.5 outline-none"
              value={activeSession?.id || ''}
              onChange={(e) => {
                const s = sessions.find((s) => s.id === e.target.value);
                if (s) handleSelectSession(s);
              }}
            >
              <option value="">Select a session...</option>
              {sessions.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.expert_name} ({s.expert_role}) - {s.message_count} msgs
                </option>
              ))}
            </select>
            <button
              onClick={handleNewSession}
              className="p-1.5 rounded bg-[var(--okw-primary)] text-white hover:bg-[var(--okw-primary-dark)]"
              title="New session"
            >
              <Plus size={14} />
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
            <ChatMessages
              messages={messages}
              isStreaming={chat.isStreaming}
              streamText={chat.streamText}
            />
            <div ref={chatEndRef} />
          </div>

          {/* Input */}
          {activeSession && (
            <div className="px-3 py-3 border-t border-[var(--okw-border)] bg-white shrink-0">
              <div className="flex gap-2">
                <input
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSendMessage()}
                  placeholder="Ask a question or share information..."
                  className="flex-1 px-3 py-2 rounded-lg border border-[var(--okw-border)] text-sm focus:outline-none focus:border-[var(--okw-primary)] focus:ring-1 focus:ring-[var(--okw-primary)]"
                  disabled={chat.isStreaming}
                />
                <button
                  onClick={handleSendMessage}
                  disabled={!chatInput.trim() || chat.isStreaming}
                  className="px-3 py-2 rounded-lg bg-[var(--okw-primary)] text-white hover:bg-[var(--okw-primary-dark)] transition-colors disabled:opacity-50"
                >
                  <Send size={16} />
                </button>
              </div>
            </div>
          )}
        </Tabs.Content>

        {/* Knowledge tab */}
        <Tabs.Content value="knowledge" className="flex-1 overflow-y-auto p-3">
          <KnowledgeList knowledge={knowledge} />
        </Tabs.Content>

        {/* Questions tab */}
        <Tabs.Content value="questions" className="flex-1 overflow-y-auto p-3">
          <QuestionList questions={questions} />
        </Tabs.Content>
      </Tabs.Root>
    </div>
  );
}
