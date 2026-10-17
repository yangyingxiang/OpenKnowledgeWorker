'use client';

import type { ReactNode } from 'react';
import { parsePdlToBlocks, type PddPhase, type PddStep, type PdlBlockType } from '@/lib/pdd/parse';
import { renderDesc, highlightPdl } from '@/lib/pdd/render';

/** Colors for each kind of PDL statement in the "Logic Flow" diagram (applied as inline styles). */
const BLOCK_COLORS: Record<PdlBlockType, { bg: string; border: string; icon: string }> = {
  given: { bg: '#eff6ff', border: '#93c5fd', icon: '📥' },
  decide: { bg: '#faf5ff', border: '#c4b5fd', icon: '🔀' },
  if: { bg: '#fefce8', border: '#fcd34d', icon: '◇' },
  else: { bg: '#fef3c7', border: '#f59e0b', icon: '◇' },
  set: { bg: '#f0fdf4', border: '#86efac', icon: '←' },
  return: { bg: '#fef2f2', border: '#fca5a5', icon: '⏎' },
  foreach: { bg: '#ecfeff', border: '#67e8f9', icon: '↻' },
};

/** Modal showing one step's description, its PDL source and a block diagram of the PDL. */
export function StepDetailPanel({
  step,
  phase,
  onClose,
}: {
  step: PddStep;
  phase: PddPhase | null;
  onClose: () => void;
}) {
  const blocks = step.pdl ? parsePdlToBlocks(step.pdl) : [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div onClick={onClose} className="absolute inset-0 bg-[rgba(0,0,0,0.35)]" />

      {/* Panel */}
      <div className="relative bg-white rounded-2xl shadow-[0_25px_50px_-12px_rgba(0,0,0,0.25)] w-[92%] max-w-[1100px] max-h-[90vh] flex flex-col overflow-hidden animate-[fadeSlideIn_0.2s_ease-out_both]">
        {/* Header */}
        <div className="px-5 py-4 border-b border-[#e5e7eb] flex items-center gap-3 bg-[#f8fafc]">
          <span className="font-[family-name:monospace] text-[0.85rem] font-bold text-[#2563eb] bg-[#eff6ff] px-2.5 py-1 rounded-md">
            {step.number}
          </span>
          <div className="flex-1">
            <h2 className="text-[1rem] font-[650] text-[#111827] m-0">{step.title}</h2>
            {phase && (
              <span className="text-[0.75rem] text-[#6b7280]">
                Phase {phase.number}: {phase.title}
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-md border-none bg-[#f3f4f6] hover:bg-[#e5e7eb] cursor-pointer text-[1rem] flex items-center justify-center text-[#6b7280]"
          >
            ✕
          </button>
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto p-5">
          {/* PDD Narrative */}
          {step.description && (
            <div className="mb-5">
              <SectionHeading>Process Description</SectionHeading>
              <div
                className="text-[0.88rem] text-[#374151] leading-[1.7] bg-[#f9fafb] rounded-[10px] px-4 py-3 border border-[#e5e7eb]"
                dangerouslySetInnerHTML={{ __html: renderDesc(step.description) }}
              />
            </div>
          )}

          {/* PDL Code */}
          {step.pdl && (
            <div className="mb-5">
              <SectionHeading>Decision Logic (PDL)</SectionHeading>
              <div className="rounded-[10px] overflow-hidden border border-[#3d3d4f]">
                <div className="px-3.5 py-2 bg-[#2d2d3f] flex items-center gap-1.5">
                  <span className="text-[0.7rem] font-semibold text-[#c4b5fd]">PDL</span>
                  <span className="text-[0.68rem] text-[#9ca3af]">Process Decision Logic</span>
                </div>
                <div className="bg-[#1e1e2e] px-4 py-3.5 overflow-x-auto">
                  <pre className="text-[0.8rem] leading-[1.7] font-[family-name:monospace] m-0 text-[#cdd6f4]">
                    <code dangerouslySetInnerHTML={{ __html: highlightPdl(step.pdl) }} />
                  </pre>
                </div>
              </div>
            </div>
          )}

          {/* Block Diagram */}
          {blocks.length > 0 && (
            <div>
              <SectionHeading>Logic Flow</SectionHeading>
              <div className="flex flex-col gap-1 px-4 py-3.5 bg-[#fafafa] rounded-[10px] border border-[#e5e7eb]">
                {blocks.map((block, i) => {
                  const bc = BLOCK_COLORS[block.type] ?? BLOCK_COLORS.set;
                  const isBranch = block.type === 'if' || block.type === 'else';
                  return (
                    <div key={i}>
                      {/* Connector arrow */}
                      {i > 0 && (
                        <div
                          className="flex flex-col items-center py-px"
                          style={{ marginLeft: block.indent * 20 + 16 }}
                        >
                          <div className="w-[1.5px] h-2.5 bg-[#d1d5db]" />
                          <div className="w-0 h-0 border-x-4 border-x-transparent border-t-[5px] border-t-[#d1d5db]" />
                        </div>
                      )}
                      <div
                        className={`flex items-center gap-2 px-3 py-1.5 border-[1.5px] text-[0.78rem] font-[family-name:monospace] text-[#1f2937] leading-[1.5] ${
                          isBranch ? 'rounded-[2px]' : 'rounded-lg'
                        }`}
                        style={{
                          marginLeft: block.indent * 20,
                          background: bc.bg,
                          borderColor: bc.border,
                        }}
                      >
                        <span className="text-[0.82rem] shrink-0">{bc.icon}</span>
                        <span>{block.text}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function SectionHeading({ children }: { children: ReactNode }) {
  return (
    <h3 className="text-[0.7rem] font-bold text-[#6b7280] uppercase tracking-[0.05em] mb-2">
      {children}
    </h3>
  );
}
