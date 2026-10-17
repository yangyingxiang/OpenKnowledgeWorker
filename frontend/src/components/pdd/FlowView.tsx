'use client';

import {
  groupPhases,
  isEarlyExit,
  isParallelPhase,
  type ParsedPdd,
  type PddPhase,
  type PddStep,
} from '@/lib/pdd/parse';
import type { StepClickHandler } from './types';

/*
 * Flow-chart rendering of the PDD: START → phases (parallel phases grouped in a dashed box) → END.
 *
 * Palette used below (Tailwind arbitrary values, kept as literal hex so they match exactly):
 *   green #16a34a / bg #f0fdf4   red #dc2626 / bg #fef2f2   blue #2563eb / bg #eff6ff
 *   purple #7c3aed   gray #6b7280   gray-light #d1d5db   gray-border #e5e7eb
 */

export function FlowView({
  parsed,
  onStepClick,
}: {
  parsed: ParsedPdd;
  onStepClick: StepClickHandler;
}) {
  const groups = groupPhases(parsed.phases);

  return (
    <div className="max-w-[800px] mx-auto py-2">
      {/* START terminal */}
      <div className="flex justify-center">
        <div className="inline-flex items-center justify-center px-7 py-1.5 rounded-[24px] bg-[#f0fdf4] border-2 border-[#16a34a] text-[#16a34a] font-bold text-[0.82rem] tracking-[0.06em]">
          START
        </div>
      </div>

      {groups.map((group, gi) => (
        <div key={gi}>
          {/* Arrow before group */}
          <div className="flex justify-center">
            <ArrowConnector />
          </div>

          {group.type === 'parallel' && group.phases.length > 1 ? (
            <>
              {/* Condition diamond before parallel container */}
              <Diamond />

              {/* Parallel wrapper */}
              <div className="border-2 border-dashed border-[#2563eb] rounded-[14px] p-4 bg-[#eff6ff] relative">
                <div className="absolute -top-2.5 left-5 bg-[#eff6ff] px-2.5 text-[0.7rem] font-semibold text-[#2563eb]">
                  Parallel execution
                </div>
                <div className="flex flex-col gap-3 mt-1">
                  {group.phases.map((phase) => (
                    <FlowPhaseCard key={phase.number} phase={phase} onStepClick={onStepClick} />
                  ))}
                </div>
              </div>
            </>
          ) : (
            <>
              {/* Check if single phase is parallel (calculation type) and add diamond */}
              {group.type === 'parallel' && <Diamond />}
              {group.phases.map((phase, pi) => (
                <div key={phase.number}>
                  {pi > 0 && (
                    <div className="flex justify-center">
                      <ArrowConnector />
                    </div>
                  )}
                  <FlowPhaseCard phase={phase} onStepClick={onStepClick} />
                </div>
              ))}
            </>
          )}
        </div>
      ))}

      {/* Arrow before END */}
      <div className="flex justify-center">
        <ArrowConnector />
      </div>

      {/* END terminal */}
      <div className="flex justify-center">
        <div className="inline-flex items-center justify-center px-7 py-1.5 rounded-[24px] bg-[#fef2f2] border-2 border-[#dc2626] text-[#dc2626] font-bold text-[0.82rem] tracking-[0.06em]">
          END
        </div>
      </div>

      <FlowLegend />
    </div>
  );
}

/* ─── Pieces ─────────────────────────────────────────────────── */

function ArrowConnector() {
  return (
    <div className="flex flex-col items-center py-1">
      <div className="w-0.5 h-5 bg-[#d1d5db]" />
      <div className="w-0 h-0 border-x-[6px] border-x-transparent border-t-[8px] border-t-[#d1d5db] -mt-px" />
    </div>
  );
}

function Diamond() {
  return (
    <div className="flex justify-center mb-2">
      <div className="w-5 h-5 bg-[#2563eb] rounded-[3px] rotate-45" />
    </div>
  );
}

function FlowStepRow({
  step,
  phase,
  onStepClick,
}: {
  step: PddStep;
  phase: PddPhase;
  onStepClick: StepClickHandler;
}) {
  const exit = isEarlyExit(step);
  return (
    <div
      onClick={() => onStepClick(step, phase)}
      className={`flex items-center gap-2 px-2.5 py-[5px] border-l-[3px] rounded-md mb-1 transition-all duration-150 ease-[ease] cursor-pointer ${
        exit
          ? 'border-l-[#dc2626] bg-[#fef2f2] hover:bg-[#fde8e8]'
          : 'border-l-transparent bg-transparent hover:bg-[#f3f4f6]'
      }`}
    >
      <span className="font-[family-name:monospace] text-[0.78rem] text-[#6b7280] min-w-[38px] shrink-0 font-semibold">
        {step.number}
      </span>
      <span className="text-[0.82rem] text-[#1f2937] leading-[1.4] flex-1">{step.title}</span>
      {step.pdl && (
        <span className="text-[0.6rem] font-[family-name:monospace] font-bold px-[5px] py-px rounded-[3px] bg-[rgba(124,58,237,0.08)] text-[#7c3aed] uppercase tracking-[0.05em] shrink-0">
          PDL
        </span>
      )}
      {exit && (
        <span className="text-[0.7rem] text-[#dc2626] font-semibold whitespace-nowrap shrink-0">
          &rarr; End
        </span>
      )}
    </div>
  );
}

function FlowPhaseCard({ phase, onStepClick }: { phase: PddPhase; onStepClick: StepClickHandler }) {
  const parallel = isParallelPhase(phase);
  const rows = phase.steps.map((step) => (
    <FlowStepRow key={step.number} step={step} phase={phase} onStepClick={onStepClick} />
  ));

  return (
    <div className="bg-white border border-[#e5e7eb] rounded-[14px] overflow-hidden shadow-[0_1px_3px_rgba(0,0,0,0.06)]">
      {/* Phase header */}
      <div className="flex items-center gap-2.5 px-3.5 py-2.5 border-b border-[#e5e7eb] bg-[#f8fafc]">
        <span className="inline-flex items-center justify-center w-7 h-7 rounded-lg bg-[#2563eb] text-white text-[0.78rem] font-bold shrink-0">
          {phase.number}
        </span>
        <span className="text-[0.88rem] font-[650] text-[#111827]">{phase.title}</span>
        <span className="ml-auto text-[0.68rem] text-[#6b7280] bg-[#f0f0f0] px-2 py-0.5 rounded-[10px] font-medium">
          {phase.steps.length} step{phase.steps.length !== 1 ? 's' : ''}
        </span>
      </div>

      {/* Phase body */}
      <div className="p-3.5">
        {parallel ? (
          /* Parallel execution container */
          <div className="border-2 border-dashed border-[#2563eb] rounded-[10px] p-3 bg-[#eff6ff] relative">
            <div className="absolute -top-2.5 left-4 bg-[#eff6ff] px-2 text-[0.68rem] font-semibold text-[#2563eb] tracking-[0.01em]">
              Parallel execution
            </div>
            <div className="grid grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-1.5 mt-1">
              {rows}
            </div>
          </div>
        ) : (
          /* Normal sequential steps */
          <div>{rows}</div>
        )}
      </div>
    </div>
  );
}

function FlowLegend() {
  return (
    <div className="flex items-center gap-[18px] flex-wrap mt-6 pt-4 border-t border-[#e5e7eb] text-[0.68rem] text-[#6b7280]">
      <div className="flex items-center gap-[5px]">
        <div className="w-3.5 h-3.5 rounded-[24px] bg-[#f0fdf4] border-[1.5px] border-[#16a34a]" />
        <span>Terminal</span>
      </div>
      <div className="flex items-center gap-[5px]">
        <div className="w-3.5 h-3.5 rounded-[3px] border-[1.5px] border-[#e5e7eb]" />
        <span>Phase</span>
      </div>
      <div className="flex items-center gap-[5px]">
        <div className="w-3.5 h-3.5 border-l-[3px] border-l-[#dc2626] bg-[#fef2f2]" />
        <span>Early exit</span>
      </div>
      <div className="flex items-center gap-[5px]">
        <div className="w-3.5 h-3.5 border-[1.5px] border-dashed border-[#2563eb] rounded-[3px] bg-[#eff6ff]" />
        <span>Parallel execution</span>
      </div>
      <div className="flex items-center gap-[5px]">
        <div className="w-2.5 h-2.5 bg-[#2563eb] rounded-[2px] rotate-45" />
        <span>Decision / branch</span>
      </div>
      <div className="flex items-center gap-[5px]">
        <span className="font-[family-name:monospace] text-[0.65rem] font-bold text-[#7c3aed] bg-[rgba(124,58,237,0.08)] px-1 rounded-[2px]">
          PDL
        </span>
        <span>Has decision logic</span>
      </div>
    </div>
  );
}
