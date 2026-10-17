'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight, History } from 'lucide-react';
import type { TestRun } from '@/lib/api';
import { formatSeconds } from '@/lib/tests/format';

/** Collapsible list of the 20 most recent test runs (collapsed by default). */
export function TestRunHistory({ testRuns }: { testRuns: TestRun[] }) {
  const [showHistory, setShowHistory] = useState(false);

  if (testRuns.length === 0) return null;

  return (
    <div className="pt-2">
      <button
        onClick={() => setShowHistory((v) => !v)}
        className="flex items-center gap-1.5 text-xs text-[var(--okw-text-muted)] hover:text-[var(--okw-text)] transition-colors"
      >
        <History size={12} />
        <span className="font-medium">History</span>
        <span className="text-[10px] opacity-60">({testRuns.length} runs)</span>
        {showHistory ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
      </button>

      {showHistory && (
        <div className="mt-2 space-y-1 animate-[fadeSlideIn_0.2s_ease-out_both]">
          {testRuns.slice(0, 20).map((run) => (
            <div
              key={run.id}
              className="flex items-center px-3 py-1.5 rounded-lg bg-white border border-[var(--okw-border)] text-xs hover:border-[var(--okw-primary)]/30 transition-colors"
            >
              <span
                className={`w-1.5 h-1.5 rounded-full mr-2 shrink-0 ${
                  run.status === 'completed' ? 'bg-[var(--okw-success)]' : 'bg-[var(--okw-warning)]'
                }`}
              />
              <span className="text-[var(--okw-text)] font-medium">{run.mode.toUpperCase()}</span>
              <span className="mx-2 text-[var(--okw-text-muted)]">|</span>
              {run.assertions_total !== null && run.assertions_total > 0 ? (
                <span className="text-[var(--okw-text)]">
                  {run.assertions_passed}/{run.assertions_total} passed
                </span>
              ) : (
                <span className="text-[var(--okw-text-muted)]">No assertions</span>
              )}
              <span className="flex-1" />
              {run.duration_ms && (
                <span className="text-[var(--okw-text-muted)] tabular-nums">
                  {formatSeconds(run.duration_ms)}s
                </span>
              )}
              <span className="ml-2 text-[var(--okw-text-muted)]">
                {new Date(run.created_at).toLocaleString()}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
