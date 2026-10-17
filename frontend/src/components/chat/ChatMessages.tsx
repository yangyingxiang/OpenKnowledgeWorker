'use client';

import type { ChatMessage } from '@/lib/api';

/** Chat transcript plus the in-progress streamed assistant reply. */
export function ChatMessages({
  messages,
  isStreaming,
  streamText,
}: {
  messages: ChatMessage[];
  isStreaming: boolean;
  streamText: string;
}) {
  return (
    <>
      {messages.map((msg, i) => (
        <div
          key={msg.id}
          className={`animate-slide-in ${
            msg.role === 'user'
              ? 'flex justify-end'
              : msg.role === 'system'
                ? 'flex justify-center'
                : 'flex justify-start'
          }`}
          style={{ animationDelay: `${i * 30}ms` }}
        >
          <div
            className={`max-w-[85%] rounded-xl px-3 py-2 text-sm ${
              msg.role === 'user'
                ? 'bg-[var(--okw-primary-light)] text-[var(--okw-text)]'
                : msg.role === 'system'
                  ? 'text-[var(--okw-text-muted)] italic text-xs'
                  : 'bg-[var(--okw-bg)] text-[var(--okw-text)]'
            }`}
          >
            <div className="whitespace-pre-wrap">{msg.content}</div>
            {msg.tool_calls && msg.tool_calls.length > 0 && (
              <div className="mt-2 pt-2 border-t border-[var(--okw-border)]">
                {msg.tool_calls.map((tc, j) => (
                  <div
                    key={j}
                    className="text-xs text-[var(--okw-text-muted)] flex items-center gap-1"
                  >
                    <span className="font-mono bg-[var(--okw-bg)] px-1 rounded">{tc.name}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      ))}
      {isStreaming && streamText && (
        <div className="flex justify-start animate-fade-in">
          <div className="max-w-[85%] rounded-xl px-3 py-2 text-sm bg-[var(--okw-bg)] text-[var(--okw-text)]">
            <div className="whitespace-pre-wrap">{streamText}</div>
            <span className="inline-block w-1.5 h-4 bg-[var(--okw-primary)] animate-pulse ml-0.5" />
          </div>
        </div>
      )}
    </>
  );
}
