'use client';

import { ChevronDown, ChevronRight, Code2, Copy, Check, Maximize2 } from 'lucide-react';
import type { PddPhase, PddStep } from '@/lib/pdd/parse';
import { renderDesc, highlightPdl } from '@/lib/pdd/render';
import type { StepClickHandler } from './types';

/** Collapsible card for one PDD phase, listing its steps on a vertical timeline. */
export function PhaseCard({
  phase,
  open,
  es,
  epdl,
  copied,
  onToggle,
  onStep,
  onPdl,
  onCopy,
  onStepClick,
}: {
  phase: PddPhase;
  open: boolean;
  es: Set<string>;
  epdl: Set<string>;
  copied: string | null;
  onToggle: () => void;
  onStep: (id: string) => void;
  onPdl: (id: string) => void;
  onCopy: (id: string, code: string) => void;
  onStepClick: StepClickHandler;
}) {
  return (
    <div
      className={`rounded-xl border-l-4 border transition-all ${
        open
          ? 'border-l-[var(--okw-primary)] border-[var(--okw-border)] shadow-sm bg-white'
          : 'border-l-gray-200 border-[var(--okw-border)] hover:border-l-gray-300 bg-white'
      }`}
    >
      {/* Phase header */}
      <button onClick={onToggle} className="w-full flex items-center gap-3 px-4 py-3.5 text-left">
        <span
          className={`shrink-0 w-9 h-9 rounded-lg flex items-center justify-center text-sm font-bold transition-colors ${
            open
              ? 'bg-[var(--okw-primary)] text-white'
              : 'bg-[var(--okw-primary-light)] text-[var(--okw-primary)]'
          }`}
        >
          {phase.number}
        </span>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-[var(--okw-text)] leading-snug">
            {phase.title}
          </h3>
          {!open && phase.description && (
            <p className="text-xs text-[var(--okw-text-muted)] truncate mt-0.5">
              {phase.description.split('\n')[0]}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-[10px] text-[var(--okw-text-muted)] bg-[var(--okw-bg)] px-2 py-0.5 rounded-full font-medium tabular-nums">
            {phase.steps.length} {phase.steps.length === 1 ? 'step' : 'steps'}
          </span>
          {open ? (
            <ChevronDown size={16} className="text-[var(--okw-text-muted)]" />
          ) : (
            <ChevronRight size={16} className="text-[var(--okw-text-muted)]" />
          )}
        </div>
      </button>

      {/* Phase body */}
      {open && (
        <div className="px-4 pb-4">
          {phase.description && (
            <div
              className="text-sm text-[var(--okw-text-muted)] mb-4 leading-relaxed pl-12"
              dangerouslySetInnerHTML={{ __html: renderDesc(phase.description) }}
            />
          )}
          <div className="pl-5 relative">
            {phase.steps.map((step, i) => (
              <StepCard
                key={step.number}
                step={step}
                phase={phase}
                isLast={i === phase.steps.length - 1}
                open={es.has(step.number)}
                pdlOpen={epdl.has(step.number)}
                isCopied={copied === step.number}
                onToggle={() => onStep(step.number)}
                onPdl={() => onPdl(step.number)}
                onCopy={(code) => onCopy(step.number, code)}
                onStepClick={onStepClick}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StepCard({
  step,
  phase,
  isLast,
  open,
  pdlOpen,
  isCopied,
  onToggle,
  onPdl,
  onCopy,
  onStepClick,
}: {
  step: PddStep;
  phase: PddPhase;
  isLast: boolean;
  open: boolean;
  pdlOpen: boolean;
  isCopied: boolean;
  onToggle: () => void;
  onPdl: () => void;
  onCopy: (code: string) => void;
  onStepClick: StepClickHandler;
}) {
  return (
    <div className="relative mb-1">
      {/* Vertical connector line + dot */}
      <div className="absolute left-0 top-0 bottom-0 flex flex-col items-center w-5">
        <div
          className={`w-[9px] h-[9px] rounded-full shrink-0 mt-[14px] z-10 ring-2 ring-white ${
            open ? 'bg-[var(--okw-primary)]' : 'bg-gray-300'
          }`}
        />
        {!isLast && <div className="w-px flex-1 bg-gray-200" />}
      </div>

      <div className="ml-7">
        {/* Step header */}
        <div className="flex items-center gap-2 py-2 group">
          <button onClick={onToggle} className="flex items-center gap-2 flex-1 min-w-0 text-left">
            <span className="font-mono text-xs font-bold text-[var(--okw-primary)] tabular-nums">
              {step.number}
            </span>
            <span
              className={`text-[13px] leading-snug ${open ? 'font-semibold text-[var(--okw-text)]' : 'text-[var(--okw-text)] group-hover:text-[var(--okw-primary)]'} transition-colors`}
            >
              {step.title}
            </span>
          </button>
          <div className="flex items-center gap-1.5 shrink-0">
            {step.pdl && (
              <span className="text-[9px] font-mono font-semibold px-1.5 py-0.5 rounded bg-purple-50 text-purple-600 uppercase tracking-wider">
                PDL
              </span>
            )}
            <button
              onClick={() => onStepClick(step, phase)}
              className="p-1 rounded hover:bg-[var(--okw-primary-light)] transition-colors opacity-0 group-hover:opacity-100"
              title="View step detail"
            >
              <Maximize2 size={12} className="text-[var(--okw-primary)]" />
            </button>
            <button onClick={onToggle}>
              {open ? (
                <ChevronDown size={14} className="text-[var(--okw-text-muted)]" />
              ) : (
                <ChevronRight size={14} className="text-[var(--okw-text-muted)]" />
              )}
            </button>
          </div>
        </div>

        {/* Step body */}
        {open && (
          <div className="pb-3">
            {step.description && (
              <div
                className="text-[13px] text-[var(--okw-text)] leading-relaxed mb-3"
                dangerouslySetInnerHTML={{ __html: renderDesc(step.description) }}
              />
            )}

            {step.pdl && (
              <div className="rounded-lg overflow-hidden border border-[#3d3d4f]">
                {/* PDL header bar */}
                <button
                  onClick={onPdl}
                  className="w-full flex items-center gap-2 px-3 py-2 bg-[#2d2d3f] text-left hover:bg-[#353548] transition-colors"
                >
                  <Code2 size={12} className="text-purple-400 shrink-0" />
                  <span className="text-[11px] font-medium text-gray-300">
                    Process Decision Logic
                  </span>
                  <div className="flex-1" />
                  {pdlOpen && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onCopy(step.pdl!);
                      }}
                      className="p-1 rounded hover:bg-[#4d4d5f] transition-colors"
                      title="Copy PDL"
                    >
                      {isCopied ? (
                        <Check size={11} className="text-green-400" />
                      ) : (
                        <Copy size={11} className="text-gray-500" />
                      )}
                    </button>
                  )}
                  {pdlOpen ? (
                    <ChevronDown size={12} className="text-gray-500 shrink-0" />
                  ) : (
                    <ChevronRight size={12} className="text-gray-500 shrink-0" />
                  )}
                </button>

                {/* PDL code */}
                {pdlOpen && (
                  <div className="bg-[#1e1e2e] px-4 py-3 overflow-x-auto">
                    <pre className="text-[12.5px] leading-[1.7] font-mono text-[#cdd6f4]">
                      <code dangerouslySetInnerHTML={{ __html: highlightPdl(step.pdl) }} />
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
