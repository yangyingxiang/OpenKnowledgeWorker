'use client';

import { useEffect, useRef } from 'react';
import { EnginePanelHeader } from './EnginePanelHeader';

/** LLM-guided engine panel: shows the raw streamed LLM text with a blinking cursor. */
export function LlmStreamPanel({
  text,
  isRunning,
  durationMs,
  error,
}: {
  text: string;
  isRunning: boolean;
  durationMs?: number;
  error?: string;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [text]);

  return (
    <div className="flex-1 flex flex-col min-w-0 rounded-xl border border-[var(--okw-border)] bg-white overflow-hidden">
      <EnginePanelHeader label="LLM Guided" isRunning={isRunning} durationMs={durationMs} />
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 max-h-[420px]">
        {error && (
          <div className="rounded-lg border border-[var(--okw-accent)] bg-red-50 px-3 py-2 mb-2">
            <p className="text-xs text-[var(--okw-accent)] font-medium">{error}</p>
          </div>
        )}
        {!text && !isRunning && !error && (
          <p className="text-center text-xs text-[var(--okw-text-muted)] py-6 opacity-50">
            No output yet
          </p>
        )}
        {!text && isRunning && !error && (
          <p className="text-center text-xs text-[var(--okw-text-muted)] py-6 animate-pulse">
            Waiting for LLM response...
          </p>
        )}
        {text && (
          <pre className="text-[11px] leading-relaxed text-[var(--okw-text)] whitespace-pre-wrap font-mono break-words">
            {text}
            {isRunning && <span className="animate-pulse">▊</span>}
          </pre>
        )}
      </div>
    </div>
  );
}
