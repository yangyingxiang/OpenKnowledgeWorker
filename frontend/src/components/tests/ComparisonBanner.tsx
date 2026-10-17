'use client';

import { Check, X, Zap } from 'lucide-react';
import { compareEngines } from '@/lib/tests/format';

/** Side-by-side mode summary: LLM vs code timings, speed-up factor and whether results match. */
export function ComparisonBanner({
  llmDuration,
  codeDuration,
  llmSummary,
  codeSummary,
}: {
  llmDuration?: number;
  codeDuration?: number;
  llmSummary?: Record<string, unknown>;
  codeSummary?: Record<string, unknown>;
}) {
  if (llmDuration === undefined || codeDuration === undefined) return null;

  const { llmSec, codeSec, faster, ratio, resultsMatch } = compareEngines(
    llmDuration,
    codeDuration,
    llmSummary,
    codeSummary,
  );

  return (
    <div className="rounded-xl border border-[var(--okw-border)] bg-white p-4 mt-3 animate-[fadeSlideIn_0.3s_ease-out_both]">
      <div className="flex items-center gap-6 flex-wrap">
        {/* LLM time */}
        <div className="text-center">
          <p className="text-[10px] uppercase tracking-wider text-[var(--okw-text-muted)] mb-0.5">
            LLM Guided
          </p>
          <p className="text-lg font-bold tabular-nums text-[var(--okw-text)]">
            {llmSec.toFixed(1)}s
          </p>
        </div>

        <span className="text-[var(--okw-text-muted)] text-sm">vs</span>

        {/* Code time */}
        <div className="text-center">
          <p className="text-[10px] uppercase tracking-wider text-[var(--okw-text-muted)] mb-0.5">
            Code Engine
          </p>
          <p className="text-lg font-bold tabular-nums text-[var(--okw-text)]">
            {codeSec.toFixed(1)}s
          </p>
        </div>

        {/* Speed badge */}
        <div className="px-3 py-1.5 rounded-full text-xs font-bold bg-[rgba(99,102,241,0.10)] text-[var(--okw-primary)]">
          <Zap size={11} className="inline -mt-0.5 mr-0.5" />
          {faster === 'code' ? 'Code' : 'LLM'} {ratio.toFixed(0)}x faster
        </div>

        <div className="flex-1" />

        {/* Match indicator */}
        <div
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold ${
            resultsMatch
              ? 'bg-[rgba(34,197,94,0.10)] text-[var(--okw-success)]'
              : 'bg-[rgba(239,68,68,0.10)] text-[var(--okw-accent)]'
          }`}
        >
          {resultsMatch ? <Check size={12} /> : <X size={12} />}
          {resultsMatch ? 'Results Match' : 'Results Differ'}
        </div>
      </div>
    </div>
  );
}
