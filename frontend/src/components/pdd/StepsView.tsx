'use client';

import type { ReactNode, ElementType } from 'react';
import {
  ChevronDown,
  ChevronRight,
  BookOpen,
  Shield,
  Hash,
  Database,
  Layers,
  Zap,
} from 'lucide-react';
import type { ParsedPdd, Row } from '@/lib/pdd/parse';
import { renderInline } from '@/lib/pdd/render';
import { PhaseCard } from './PhaseCard';
import type { StepClickHandler } from './types';

interface StepsProps {
  p: ParsedPdd;
  /** Expanded phase numbers */
  ep: Set<number>;
  /** Expanded step numbers */
  es: Set<string>;
  /** Step numbers whose PDL block is expanded */
  epdl: Set<string>;
  /** Expanded meta sections (keys of ParsedPdd) */
  esec: Set<string>;
  copied: string | null;
  onPhase: (n: number) => void;
  onStep: (id: string) => void;
  onPdl: (id: string) => void;
  onSec: (id: string) => void;
  onCopy: (id: string, code: string) => void;
  onStepClick: StepClickHandler;
}

/** "Steps" view: accordion sections for the PDD tables plus an expandable list of phases/steps. */
export function StepsView({
  p,
  ep,
  es,
  epdl,
  esec,
  copied,
  onPhase,
  onStep,
  onPdl,
  onSec,
  onCopy,
  onStepClick,
}: StepsProps) {
  return (
    <div className="space-y-3">
      {/* Meta sections */}
      {p.keyConcepts.length > 0 && (
        <MetaSection
          title="Key Concepts"
          icon={BookOpen}
          count={p.keyConcepts.length}
          open={esec.has('keyConcepts')}
          toggle={() => onSec('keyConcepts')}
        >
          <div className="space-y-2.5">
            {p.keyConcepts.map((row, i) => {
              const vals = Object.values(row);
              return (
                <div key={i} className="flex gap-3 text-sm">
                  <span
                    className="font-semibold text-[var(--okw-text)] min-w-[160px] shrink-0"
                    dangerouslySetInnerHTML={{ __html: renderInline(vals[0] || '') }}
                  />
                  <span
                    className="text-[var(--okw-text-muted)] leading-relaxed"
                    dangerouslySetInnerHTML={{ __html: renderInline(vals[1] || '') }}
                  />
                </div>
              );
            })}
          </div>
        </MetaSection>
      )}

      {p.variables.length > 0 && (
        <MetaSection
          title="Variable Reference"
          icon={Database}
          count={p.variables.length}
          open={esec.has('variables')}
          toggle={() => onSec('variables')}
        >
          <DataTable rows={p.variables} />
        </MetaSection>
      )}

      {p.outputs.length > 0 && (
        <MetaSection
          title="Outputs"
          icon={Zap}
          count={p.outputs.length}
          open={esec.has('outputs')}
          toggle={() => onSec('outputs')}
        >
          <DataTable rows={p.outputs} />
        </MetaSection>
      )}

      {/* Phases */}
      {p.phases.length > 0 && (
        <div className="space-y-3 pt-2">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-[var(--okw-text-muted)] flex items-center gap-2">
            <Layers size={13} className="text-[var(--okw-primary)]" /> Process
          </h2>
          {p.phases.map((phase) => (
            <PhaseCard
              key={phase.number}
              phase={phase}
              open={ep.has(phase.number)}
              es={es}
              epdl={epdl}
              copied={copied}
              onToggle={() => onPhase(phase.number)}
              onStep={onStep}
              onPdl={onPdl}
              onCopy={onCopy}
              onStepClick={onStepClick}
            />
          ))}
        </div>
      )}

      {/* Business Rules */}
      {p.businessRules.length > 0 && (
        <MetaSection
          title="Business Rules"
          icon={Shield}
          count={p.businessRules.length}
          open={esec.has('businessRules')}
          toggle={() => onSec('businessRules')}
        >
          <BusinessRulesTable rows={p.businessRules} />
        </MetaSection>
      )}

      {/* Decision Priority */}
      {p.decisionPriority.length > 0 && (
        <MetaSection
          title="Decision Priority"
          icon={Hash}
          count={p.decisionPriority.length}
          open={esec.has('decisionPriority')}
          toggle={() => onSec('decisionPriority')}
        >
          <div className="space-y-2.5">
            {p.decisionPriority.map((row, i) => {
              const vals = Object.values(row);
              return (
                <div key={i} className="flex items-start gap-3">
                  <span className="shrink-0 w-8 h-8 rounded-full bg-[var(--okw-primary-light)] text-[var(--okw-primary)] flex items-center justify-center font-bold text-sm">
                    {vals[0]}
                  </span>
                  <p
                    className="text-sm text-[var(--okw-text)] pt-1.5 leading-relaxed"
                    dangerouslySetInnerHTML={{ __html: renderInline(vals[1] || '') }}
                  />
                </div>
              );
            })}
          </div>
        </MetaSection>
      )}
    </div>
  );
}

/* ─── Meta Section (accordion) ───────────────────────────────── */

function MetaSection({
  title,
  icon: Icon,
  count,
  open,
  toggle,
  children,
}: {
  title: string;
  icon: ElementType;
  count: number;
  open: boolean;
  toggle: () => void;
  children: ReactNode;
}) {
  return (
    <div
      className={`rounded-xl border overflow-hidden transition-colors ${open ? 'border-[var(--okw-border)] shadow-sm' : 'border-[var(--okw-border)]'}`}
    >
      <button
        onClick={toggle}
        className="w-full flex items-center gap-2.5 px-4 py-3 bg-[var(--okw-bg)] hover:bg-gray-50 transition-colors text-left"
      >
        {open ? (
          <ChevronDown size={14} className="text-[var(--okw-text-muted)] shrink-0" />
        ) : (
          <ChevronRight size={14} className="text-[var(--okw-text-muted)] shrink-0" />
        )}
        <Icon size={14} className="text-[var(--okw-primary)] shrink-0" />
        <span className="text-sm font-semibold text-[var(--okw-text)]">{title}</span>
        <span className="text-[10px] text-[var(--okw-text-muted)] ml-auto tabular-nums">
          {count} items
        </span>
      </button>
      {open && (
        <div className="px-4 py-3 bg-white border-t border-[var(--okw-border)]">{children}</div>
      )}
    </div>
  );
}

/* ─── Tables ─────────────────────────────────────────────────── */

function DataTable({ rows }: { rows: Row[] }) {
  if (!rows.length) return null;
  const headers = Object.keys(rows[0]);
  return (
    <div className="overflow-x-auto -mx-1">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--okw-border)]">
            {headers.map((h) => (
              <th
                key={h}
                className="text-left py-1.5 px-2 text-[10px] font-semibold text-[var(--okw-text-muted)] uppercase tracking-wider"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b border-[var(--okw-border)] last:border-0">
              {headers.map((h, j) => (
                <td
                  key={j}
                  className="py-1.5 px-2 text-[var(--okw-text)] text-xs"
                  dangerouslySetInnerHTML={{ __html: renderInline(row[h] || '') }}
                />
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function BusinessRulesTable({ rows }: { rows: Row[] }) {
  return (
    <div className="overflow-x-auto -mx-1">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b-2 border-[var(--okw-primary)]">
            {Object.keys(rows[0]).map((h) => (
              <th
                key={h}
                className="text-left py-2 px-2 text-[10px] font-semibold text-[var(--okw-text)] uppercase tracking-wider bg-[var(--okw-primary-light)]"
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr
              key={i}
              className="border-b border-[var(--okw-border)] hover:bg-[var(--okw-bg)] transition-colors"
            >
              {Object.entries(row).map(([, v], j) => (
                <td
                  key={j}
                  className={`py-2 px-2 ${j === 0 ? 'font-mono text-[var(--okw-primary)] font-semibold text-xs whitespace-nowrap' : 'text-[var(--okw-text)] text-xs'}`}
                  dangerouslySetInnerHTML={{ __html: renderInline(v) }}
                />
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
