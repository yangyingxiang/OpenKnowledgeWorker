'use client';

import { useState, useMemo, type ElementType } from 'react';
import {
  Code2,
  Layers,
  Shield,
  Maximize2,
  Minimize2,
  FileText,
  Database,
  CircleDot,
  GitBranch,
  Eye,
  EyeOff,
  List,
} from 'lucide-react';
import {
  parsePddContent,
  countSteps,
  countPdlBlocks,
  stepNumbersWithPdl,
  PDD_TABLE_SECTIONS,
  type PddPhase,
  type PddStep,
} from '@/lib/pdd/parse';
import { fallbackMarkdown } from '@/lib/pdd/render';
import { StepsView } from './StepsView';
import { FlowView } from './FlowView';
import { StepDetailPanel } from './StepDetailPanel';

type ViewMode = 'steps' | 'flow' | 'source';

/**
 * Structured viewer for a PDD (SOP) markdown document.
 * Offers three views: an expandable step list, a flow chart, and the raw markdown source.
 * Falls back to a simple markdown render when the content can't be parsed.
 */
export function PddViewer({ content }: { content: string }) {
  const parsed = useMemo(() => parsePddContent(content), [content]);

  const [expandedPhases, setExpandedPhases] = useState<Set<number>>(
    () => new Set(parsed?.phases.map((p) => p.number) ?? []),
  );
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set());
  const [expandedPdl, setExpandedPdl] = useState<Set<string>>(new Set());
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());
  const [showAllPdl, setShowAllPdl] = useState(false);
  const [viewMode, setViewMode] = useState<ViewMode>('flow');
  const [copiedPdl, setCopiedPdl] = useState<string | null>(null);
  const [detailStep, setDetailStep] = useState<PddStep | null>(null);
  const [detailPhase, setDetailPhase] = useState<PddPhase | null>(null);

  const handleStepClick = (step: PddStep, phase: PddPhase) => {
    setDetailStep(step);
    setDetailPhase(phase);
  };

  // Fallback: render as raw markdown
  if (!parsed) {
    return (
      <div
        className="pdd-content"
        dangerouslySetInnerHTML={{ __html: fallbackMarkdown(content) }}
      />
    );
  }

  const totalSteps = countSteps(parsed);
  const totalPdl = countPdlBlocks(parsed);

  const toggle = <T,>(setter: React.Dispatch<React.SetStateAction<Set<T>>>, val: T) => {
    setter((prev) => {
      const n = new Set(prev);
      if (n.has(val)) n.delete(val);
      else n.add(val);
      return n;
    });
  };

  const expandAll = () => {
    setExpandedPhases(new Set(parsed.phases.map((p) => p.number)));
    setExpandedSteps(new Set(parsed.phases.flatMap((p) => p.steps.map((s) => s.number))));
    setExpandedPdl(new Set(stepNumbersWithPdl(parsed)));
    setExpandedSections(new Set(PDD_TABLE_SECTIONS));
    setShowAllPdl(true);
  };
  const collapseAll = () => {
    setExpandedPhases(new Set());
    setExpandedSteps(new Set());
    setExpandedPdl(new Set());
    setExpandedSections(new Set());
    setShowAllPdl(false);
  };
  const toggleAllPdl = () => {
    if (showAllPdl) setExpandedPdl(new Set());
    else setExpandedPdl(new Set(stepNumbersWithPdl(parsed)));
    setShowAllPdl(!showAllPdl);
  };
  const copyPdl = (id: string, code: string) => {
    navigator.clipboard.writeText(code);
    setCopiedPdl(id);
    setTimeout(() => setCopiedPdl(null), 2000);
  };

  const stats = [
    { Icon: Layers, n: parsed.phases.length, label: 'Phases', cls: 'bg-red-50 text-red-700' },
    { Icon: CircleDot, n: totalSteps, label: 'Steps', cls: 'bg-blue-50 text-blue-700' },
    { Icon: Code2, n: totalPdl, label: 'PDL Blocks', cls: 'bg-purple-50 text-purple-700' },
    {
      Icon: Database,
      n: parsed.variables.length,
      label: 'Variables',
      cls: 'bg-green-50 text-green-700',
    },
    {
      Icon: Shield,
      n: parsed.businessRules.length,
      label: 'Rules',
      cls: 'bg-orange-50 text-orange-700',
    },
  ];

  const viewButtons = [
    { v: 'steps', l: 'Steps', I: List },
    { v: 'flow', l: 'Flow', I: GitBranch },
    { v: 'source', l: 'Source', I: FileText },
  ] as const;

  return (
    <div>
      {/* ── Header ── */}
      <div className="mb-5">
        <h1 className="text-xl font-bold text-[var(--okw-text)] leading-tight">
          {parsed.title || 'Standard Operating Procedure'}
        </h1>
        {parsed.purpose && (
          <p className="mt-2 text-sm text-[var(--okw-text-muted)] leading-relaxed max-w-[800px]">
            {parsed.purpose}
          </p>
        )}
      </div>

      {/* ── Stats ── */}
      <div className="flex items-center gap-2.5 mb-4 flex-wrap">
        {stats
          .filter((s) => s.n > 0)
          .map((s) => (
            <div
              key={s.label}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium ${s.cls}`}
            >
              <s.Icon size={12} /> {s.n} {s.label}
            </div>
          ))}
      </div>

      {/* ── Toolbar ── */}
      <div className="flex items-center gap-2 mb-5 pb-4 border-b border-[var(--okw-border)]">
        <div className="flex items-center bg-[var(--okw-bg)] rounded-lg p-0.5">
          {viewButtons.map((b) => (
            <button
              key={b.v}
              onClick={() => setViewMode(b.v)}
              className={`flex items-center gap-1 px-2.5 py-1.5 rounded-md text-xs font-medium transition-all ${
                viewMode === b.v
                  ? 'bg-white text-[var(--okw-text)] shadow-sm'
                  : 'text-[var(--okw-text-muted)] hover:text-[var(--okw-text)]'
              }`}
            >
              <b.I size={12} /> {b.l}
            </button>
          ))}
        </div>
        <div className="flex-1" />
        {viewMode === 'steps' && (
          <>
            <ToolBtn
              onClick={toggleAllPdl}
              icon={showAllPdl ? EyeOff : Eye}
              label={showAllPdl ? 'Hide PDL' : 'Show PDL'}
            />
            <ToolBtn onClick={expandAll} icon={Maximize2} label="Expand All" />
            <ToolBtn onClick={collapseAll} icon={Minimize2} label="Collapse All" />
          </>
        )}
      </div>

      {/* ── Views ── */}
      {viewMode === 'steps' && (
        <StepsView
          p={parsed}
          ep={expandedPhases}
          es={expandedSteps}
          epdl={expandedPdl}
          esec={expandedSections}
          copied={copiedPdl}
          onPhase={(n) => toggle(setExpandedPhases, n)}
          onStep={(id) => toggle(setExpandedSteps, id)}
          onPdl={(id) => toggle(setExpandedPdl, id)}
          onSec={(id) => toggle(setExpandedSections, id)}
          onCopy={copyPdl}
          onStepClick={handleStepClick}
        />
      )}
      {viewMode === 'flow' && <FlowView parsed={parsed} onStepClick={handleStepClick} />}
      {viewMode === 'source' && (
        <div className="rounded-xl bg-[#1e1e2e] p-5 overflow-x-auto">
          <pre className="text-[13px] text-[#cdd6f4] font-mono leading-relaxed whitespace-pre-wrap">
            {content}
          </pre>
        </div>
      )}

      {/* Step Detail Overlay (shared across views) */}
      {detailStep && (
        <StepDetailPanel
          step={detailStep}
          phase={detailPhase}
          onClose={() => {
            setDetailStep(null);
            setDetailPhase(null);
          }}
        />
      )}
    </div>
  );
}

function ToolBtn({
  onClick,
  icon: Icon,
  label,
}: {
  onClick: () => void;
  icon: ElementType;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-1 px-2 py-1 rounded text-xs text-[var(--okw-text-muted)] hover:text-[var(--okw-text)] hover:bg-[var(--okw-bg)] transition-colors"
    >
      <Icon size={12} /> {label}
    </button>
  );
}
