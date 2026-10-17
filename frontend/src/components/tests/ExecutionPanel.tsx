'use client';

import { useEffect, useRef } from 'react';
import type { TraceStep } from '@/lib/tests/execState';
import { formatUsd } from '@/lib/tests/format';
import { EnginePanelHeader } from './EnginePanelHeader';
import { TraceStepCard } from './TraceStepCard';

/** Code-engine panel: streams trace step cards and shows the final result summary. */
export function ExecutionPanel({
  label,
  steps,
  isRunning,
  durationMs,
  error,
  summary,
}: {
  label: string;
  steps: TraceStep[];
  isRunning: boolean;
  durationMs?: number;
  error?: string;
  summary?: Record<string, unknown>;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll as steps arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [steps.length]);

  return (
    <div className="flex-1 flex flex-col min-w-0 rounded-xl border border-[var(--okw-border)] bg-white overflow-hidden">
      <EnginePanelHeader label={label} isRunning={isRunning} durationMs={durationMs} />

      {/* Trace steps */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-2 space-y-1.5 max-h-[420px]">
        {error && (
          <div className="rounded-lg border border-[var(--okw-accent)] bg-red-50 px-3 py-2 mx-1 mt-1">
            <p className="text-xs text-[var(--okw-accent)] font-medium">{error}</p>
          </div>
        )}
        {steps.length === 0 && !isRunning && !error && (
          <p className="text-center text-xs text-[var(--okw-text-muted)] py-6 opacity-50">
            No steps yet
          </p>
        )}
        {steps.length === 0 && isRunning && !error && (
          <p className="text-center text-xs text-[var(--okw-text-muted)] py-6 animate-pulse">
            Waiting for trace steps...
          </p>
        )}
        {steps.map((step, i) => (
          <TraceStepCard key={step.step_id} step={step} index={i} />
        ))}

        {/* Final result summary */}
        {!isRunning &&
          summary &&
          (summary.total_monthly !== undefined || summary.total_annual !== undefined) && (
            <FinalResultSummary summary={summary} />
          )}
      </div>
    </div>
  );
}

function FinalResultSummary({ summary }: { summary: Record<string, unknown> }) {
  const streams = summary.stream_incomes;
  const streamEntries =
    streams && typeof streams === 'object' ? Object.entries(streams as Record<string, number>) : [];
  const flags = Array.isArray(summary.flags) ? (summary.flags as string[]) : [];

  return (
    <div className="rounded-lg border-2 border-[var(--okw-primary)] bg-[var(--okw-primary)]/5 p-3 mt-2">
      <div className="flex items-center gap-2 mb-2">
        <div className="w-1.5 h-1.5 rounded-full bg-[var(--okw-primary)]" />
        <span className="text-xs font-bold uppercase tracking-wider text-[var(--okw-primary)]">
          Final Result
        </span>
      </div>
      <div className="grid grid-cols-2 gap-2 mb-2">
        <div>
          <p className="text-[10px] uppercase tracking-wider text-[var(--okw-text-muted)]">
            Monthly Income
          </p>
          <p className="text-lg font-bold tabular-nums text-[var(--okw-text)]">
            {formatUsd(summary.total_monthly)}
          </p>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-wider text-[var(--okw-text-muted)]">
            Annual Income
          </p>
          <p className="text-lg font-bold tabular-nums text-[var(--okw-text)]">
            {formatUsd(summary.total_annual)}
          </p>
        </div>
      </div>
      {/* Stream breakdown */}
      {streamEntries.length > 0 && (
        <div className="border-t border-[var(--okw-border)] pt-2 mt-1">
          <p className="text-[10px] uppercase tracking-wider text-[var(--okw-text-muted)] mb-1">
            Income Streams
          </p>
          {streamEntries.map(([name, amount]) => (
            <div key={name} className="flex items-center justify-between text-xs py-0.5">
              <span className="text-[var(--okw-text)]">{name}</span>
              <span className="font-semibold tabular-nums text-[var(--okw-text)]">
                {formatUsd(amount)}
                <span className="text-[var(--okw-text-muted)] font-normal">/mo</span>
              </span>
            </div>
          ))}
        </div>
      )}
      {/* Flags count */}
      {flags.length > 0 && (
        <div className="border-t border-[var(--okw-border)] pt-2 mt-2">
          <span className="text-[10px] uppercase tracking-wider font-semibold text-[var(--okw-warning)]">
            {flags.length} flag(s)
          </span>
        </div>
      )}
    </div>
  );
}
