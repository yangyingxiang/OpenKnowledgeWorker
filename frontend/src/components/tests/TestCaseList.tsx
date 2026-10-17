'use client';

import type { RefObject } from 'react';
import { Check, Loader2, TestTube, Trash2, X } from 'lucide-react';
import type { TestCase } from '@/lib/api';
import type { LiveTestState } from '@/lib/tests/execState';
import { formatSeconds } from '@/lib/tests/format';

/** Compact, selectable list of test cases with live status, duration and a delete button. */
export function TestCaseList({
  testCases,
  liveTests,
  displayTestId,
  chatHighlightTestId,
  chatHighlightRef,
  selectedCases,
  onToggleCase,
  onToggleAll,
  onRowClick,
  onDelete,
}: {
  testCases: TestCase[];
  liveTests: Record<string, LiveTestState>;
  displayTestId: string | null;
  chatHighlightTestId: string | null;
  chatHighlightRef: RefObject<HTMLDivElement | null>;
  selectedCases: Set<string>;
  onToggleCase: (id: string) => void;
  onToggleAll: () => void;
  onRowClick: (id: string) => void;
  onDelete: (id: string) => void;
}) {
  return (
    <div className="rounded-xl border border-[var(--okw-border)] bg-white overflow-hidden">
      {/* Select-all header */}
      <div className="flex items-center gap-2 px-3 py-1.5 bg-[var(--okw-bg)] border-b border-[var(--okw-border)]">
        <label className="flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            checked={selectedCases.size === testCases.length && testCases.length > 0}
            onChange={onToggleAll}
            className="accent-[var(--okw-primary)]"
          />
          <span className="text-[10px] uppercase tracking-wider font-semibold text-[var(--okw-text-muted)]">
            {selectedCases.size > 0 ? `${selectedCases.size} selected` : 'Select all'}
          </span>
        </label>
      </div>

      {testCases.map((tc) => {
        const live = liveTests[tc.id];
        const isActive = displayTestId === tc.id;
        const isChatHighlight = chatHighlightTestId === tc.id;
        return (
          <div
            key={tc.id}
            ref={isChatHighlight ? chatHighlightRef : undefined}
            className={`flex items-center gap-2 px-3 py-2 border-b border-[var(--okw-border)] last:border-b-0 cursor-pointer transition-colors ${
              isChatHighlight
                ? 'bg-[#f59e0b]/10 border-l-2 border-l-[#f59e0b]'
                : isActive
                  ? 'bg-[var(--okw-primary)]/5'
                  : 'hover:bg-[var(--okw-bg)]'
            }`}
            onClick={() => onRowClick(tc.id)}
          >
            <label
              className="flex items-center cursor-pointer"
              onClick={(e) => e.stopPropagation()}
            >
              <input
                type="checkbox"
                checked={selectedCases.has(tc.id)}
                onChange={() => onToggleCase(tc.id)}
                className="accent-[var(--okw-primary)]"
              />
            </label>

            <div className="flex-1 min-w-0">
              <span className="text-xs font-medium text-[var(--okw-text)]">{tc.test_name}</span>
              {tc.description && (
                <span className="text-[11px] text-[var(--okw-text-muted)] ml-2">
                  {tc.description}
                </span>
              )}
            </div>

            <LiveStatus live={live} />

            {/* Duration */}
            {live?.durationMs && (
              <span className="text-[10px] tabular-nums text-[var(--okw-text-muted)] shrink-0">
                {formatSeconds(live.durationMs)}s
              </span>
            )}

            {/* Delete */}
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete(tc.id);
              }}
              className="p-0.5 rounded hover:bg-red-50 text-[var(--okw-text-muted)] hover:text-red-600 shrink-0 opacity-0 group-hover:opacity-100"
              onMouseEnter={(e) => (e.currentTarget.style.opacity = '1')}
              onMouseLeave={(e) => (e.currentTarget.style.opacity = '0.3')}
            >
              <Trash2 size={12} />
            </button>
          </div>
        );
      })}
    </div>
  );
}

/** Status indicator for one test case: spinner, pass count, check or error cross. */
function LiveStatus({ live }: { live: LiveTestState | undefined }) {
  return (
    <>
      {live?.status === 'running' && (
        <Loader2 size={12} className="animate-spin text-[var(--okw-warning)] shrink-0" />
      )}
      {live?.status === 'done' && live.total !== undefined && live.total > 0 && (
        <span
          className={`text-[11px] font-semibold shrink-0 ${
            live.passed === live.total ? 'text-[var(--okw-success)]' : 'text-[var(--okw-accent)]'
          }`}
        >
          {live.passed === live.total ? (
            <Check size={11} className="inline -mt-0.5" />
          ) : (
            <X size={11} className="inline -mt-0.5" />
          )}{' '}
          {live.passed}/{live.total}
        </span>
      )}
      {live?.status === 'done' && (live.total === undefined || live.total === 0) && (
        <Check size={12} className="text-[var(--okw-success)] shrink-0" />
      )}
      {live?.status === 'error' && <X size={12} className="text-[var(--okw-accent)] shrink-0" />}
    </>
  );
}

/** Shown instead of the list when the process has no test cases yet. */
export function TestCasesEmptyState({
  onCreateClick,
  onUploadClick,
  isUploading,
}: {
  onCreateClick: () => void;
  onUploadClick: () => void;
  isUploading: boolean;
}) {
  return (
    <div className="text-center py-20 text-[var(--okw-text-muted)] animate-[fadeSlideIn_0.3s_ease-out_both]">
      <TestTube size={40} className="mx-auto mb-3 opacity-30" />
      <h3 className="text-lg font-semibold text-[var(--okw-text)]">No test cases</h3>
      <p className="text-sm mt-1 mb-4">Add test cases to validate the process</p>
      <div className="flex gap-2 justify-center">
        <button
          onClick={onCreateClick}
          className="px-4 py-2 rounded-lg bg-[var(--okw-primary)] text-white text-sm font-medium hover:bg-[var(--okw-primary-dark)]"
        >
          Create Test Case
        </button>
        <button
          onClick={onUploadClick}
          disabled={isUploading}
          className="px-4 py-2 rounded-lg border border-[var(--okw-border)] text-sm font-medium text-[var(--okw-text)] hover:bg-white disabled:opacity-50"
        >
          {isUploading ? 'Uploading...' : 'Upload Tests'}
        </button>
      </div>
    </div>
  );
}
