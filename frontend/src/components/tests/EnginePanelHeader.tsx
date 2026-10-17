'use client';

import { Clock, Loader2 } from 'lucide-react';
import { useElapsedTimer } from '@/lib/hooks/useElapsedTimer';
import { formatSeconds } from '@/lib/tests/format';

/**
 * Header shared by the LLM and Code engine panels: label on the left, timer on the right.
 * Shows the final duration when known, otherwise a live timer while running, otherwise "--".
 */
export function EnginePanelHeader({
  label,
  isRunning,
  durationMs,
}: {
  label: string;
  isRunning: boolean;
  durationMs?: number;
}) {
  const elapsedStr = useElapsedTimer(isRunning);

  const timeDisplay =
    durationMs !== undefined ? formatSeconds(durationMs) : isRunning ? elapsedStr : '--';

  return (
    <div className="flex items-center justify-between px-3 py-2 border-b border-[var(--okw-border)] bg-[var(--okw-bg)]">
      <span className="text-xs font-semibold text-[var(--okw-text)] tracking-wide uppercase">
        {label}
      </span>
      <span
        className={`flex items-center gap-1 text-xs tabular-nums ${
          isRunning ? 'text-[var(--okw-warning)]' : 'text-[var(--okw-text-muted)]'
        }`}
      >
        {isRunning && <Loader2 size={11} className="animate-spin" />}
        <Clock size={10} />
        {timeDisplay}s
      </span>
    </div>
  );
}
