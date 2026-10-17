'use client';

import { useEffect, useMemo, useRef } from 'react';
import { X, Check, ArrowRight } from 'lucide-react';
import { condenseDiff, type DiffLine } from '@/lib/pdd/diff';

export interface PddEditInfo {
  sectionPath: string;
  reason: string;
  beforeContent: string;
  afterContent: string;
  diff: DiffLine[];
}

/** Modal showing a before/after comparison when the PDD is edited by the chat agent. */
export function DiffOverlay({
  edit,
  onAccept,
  onRevert,
}: {
  edit: PddEditInfo;
  onAccept: () => void;
  onRevert: () => void;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Condense diff: show only lines near changes (context=3)
  const condensed = useMemo(() => condenseDiff(edit.diff, 3), [edit.diff]);

  // Auto-scroll to first change
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const firstChange = el.querySelector('.diff-added, .diff-removed');
    if (firstChange) {
      setTimeout(() => firstChange.scrollIntoView({ behavior: 'smooth', block: 'center' }), 100);
    }
  }, [condensed]);

  const addedCount = edit.diff.filter((d) => d.type === 'added').length;
  const removedCount = edit.diff.filter((d) => d.type === 'removed').length;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm animate-fade-in">
      <div className="flex flex-col bg-white rounded-xl shadow-2xl overflow-hidden border border-[var(--okw-border)] w-[90%] max-w-[1000px] max-h-[85vh]">
        {/* Header */}
        <div className="px-4 py-3 border-b border-[var(--okw-border)] flex items-center gap-3 bg-gradient-to-r from-blue-50 to-indigo-50 shrink-0">
          <div className="w-8 h-8 rounded-lg bg-blue-100 flex items-center justify-center shrink-0">
            <ArrowRight size={16} className="text-blue-600" />
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-sm font-semibold text-[var(--okw-text)]">Proposed Change</h3>
            <p className="text-xs text-[var(--okw-text-muted)] truncate">{edit.reason}</p>
          </div>
          <div className="flex items-center gap-2 text-xs shrink-0">
            {addedCount > 0 && (
              <span className="px-2 py-0.5 rounded-full bg-green-100 text-green-700 font-medium">
                +{addedCount}
              </span>
            )}
            {removedCount > 0 && (
              <span className="px-2 py-0.5 rounded-full bg-red-100 text-red-700 font-medium">
                -{removedCount}
              </span>
            )}
          </div>
          <button
            onClick={onRevert}
            className="p-1.5 rounded-lg hover:bg-white/80 transition-colors shrink-0"
            title="Close and revert"
          >
            <X size={16} className="text-[var(--okw-text-muted)]" />
          </button>
        </div>

        {/* Diff content */}
        <div ref={scrollRef} className="overflow-y-auto px-1 py-2 bg-[#fafbfc] flex-1 min-h-0">
          <div className="font-mono text-[12px] leading-[1.8]">
            {condensed.map((line, i) => {
              if (line.type === 'separator') {
                return (
                  <div
                    key={`sep-${i}`}
                    className="px-4 py-1 text-center text-[10px] text-gray-400 select-none bg-gray-50 border-y border-gray-100"
                  >
                    ···
                  </div>
                );
              }
              return (
                <div
                  key={i}
                  className={`px-4 whitespace-pre-wrap ${
                    line.type === 'added'
                      ? 'diff-added bg-green-50 text-green-900 border-l-2 border-green-400'
                      : line.type === 'removed'
                        ? 'diff-removed bg-red-50 text-red-900 border-l-2 border-red-300 opacity-70'
                        : 'text-gray-600 border-l-2 border-transparent'
                  }`}
                >
                  <span className="inline-block w-4 text-right mr-3 text-gray-400 select-none text-[10px]">
                    {line.type === 'added' ? '+' : line.type === 'removed' ? '-' : ' '}
                  </span>
                  {line.text}
                </div>
              );
            })}
          </div>
        </div>

        {/* Footer */}
        <div className="px-4 py-2.5 border-t border-[var(--okw-border)] flex items-center justify-end gap-3 bg-white shrink-0">
          <button
            onClick={onRevert}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg border border-red-200 text-red-600 text-xs font-medium hover:bg-red-50 transition-colors"
          >
            <X size={13} /> Revert
          </button>
          <button
            onClick={onAccept}
            className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg bg-green-600 text-white text-xs font-medium hover:bg-green-700 transition-colors"
          >
            <Check size={13} /> Accept
          </button>
        </div>
      </div>
    </div>
  );
}
