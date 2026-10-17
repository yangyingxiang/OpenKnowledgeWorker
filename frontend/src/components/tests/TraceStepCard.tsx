'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';
import type { TraceStep } from '@/lib/tests/execState';
import { decisionStyle } from '@/lib/tests/format';

/** One step of an execution trace: id, title, result value, decision badge and rationale. */
export function TraceStepCard({ step, index }: { step: TraceStep; index: number }) {
  const [showRationale, setShowRationale] = useState(false);
  const colors = decisionStyle(step.decision);

  return (
    <div
      className="rounded-lg border border-[var(--okw-border)] bg-white overflow-hidden"
      style={{
        borderLeftWidth: 3,
        borderLeftColor: colors.border,
        animation: `fadeSlideIn 0.3s ease-out ${index * 60}ms both`,
      }}
    >
      <div className="px-3 py-2 flex items-start gap-2">
        {/* Step ID badge */}
        <code className="shrink-0 mt-0.5 text-[10px] font-mono px-1.5 py-0.5 rounded bg-[var(--okw-bg)] text-[var(--okw-text-muted)]">
          {step.step_id}
        </code>

        {/* Title + result value */}
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-[var(--okw-text)] leading-snug">{step.title}</p>
          {step.result_value !== null && step.result_value !== undefined && (
            <p className="text-[11px] text-[var(--okw-text-muted)] mt-0.5 truncate">
              {step.result_label ? `${step.result_label}: ` : ''}
              {String(step.result_value)}
            </p>
          )}
        </div>

        {/* Decision badge */}
        <span
          className="shrink-0 text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full"
          style={{ background: colors.bg, color: colors.text }}
        >
          {step.decision}
        </span>
      </div>

      {/* Rationale toggle */}
      {step.rationale && (
        <div className="border-t border-[var(--okw-border)]">
          <button
            onClick={() => setShowRationale((v) => !v)}
            className="flex items-center gap-1 px-3 py-1 text-[10px] text-[var(--okw-text-muted)] hover:text-[var(--okw-text)] w-full"
          >
            {showRationale ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
            Rationale
          </button>
          {showRationale && (
            <p className="px-3 pb-2 text-[11px] text-[var(--okw-text-muted)] leading-relaxed whitespace-pre-wrap">
              {step.rationale}
              {step.rule_citation && (
                <span className="block mt-1 text-[10px] italic opacity-70">
                  Rule: {step.rule_citation}
                </span>
              )}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
