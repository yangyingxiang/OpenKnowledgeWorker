'use client';

import { Clock, Columns, Loader2, Play, Plus, Square, Upload } from 'lucide-react';
import { useElapsedTimer } from '@/lib/hooks/useElapsedTimer';
import type { RunMode } from '@/lib/tests/execState';

const RUN_MODES: RunMode[] = ['llm', 'code', 'both'];

/** Top bar of the Test Suite page: run mode selector, run/stop, global timer, upload and add. */
export function TestsToolbar({
  runMode,
  onRunModeChange,
  isRunning,
  onRun,
  onStop,
  canRun,
  selectedCount,
  isUploading,
  onUploadClick,
  onAddClick,
}: {
  runMode: RunMode;
  onRunModeChange: (mode: RunMode) => void;
  isRunning: boolean;
  onRun: () => void;
  onStop: () => void;
  canRun: boolean;
  selectedCount: number;
  isUploading: boolean;
  onUploadClick: () => void;
  onAddClick: () => void;
}) {
  const globalElapsed = useElapsedTimer(isRunning);

  return (
    <div className="px-4 py-2.5 border-b border-[var(--okw-border)] bg-[var(--okw-bg)] flex items-center gap-2 flex-wrap">
      {/* Mode selector */}
      <div className="flex items-center gap-0 border border-[var(--okw-border)] rounded-lg overflow-hidden">
        {RUN_MODES.map((mode) => (
          <button
            key={mode}
            onClick={() => onRunModeChange(mode)}
            className={`px-3 py-1.5 text-xs font-medium transition-colors ${
              runMode === mode
                ? 'bg-[var(--okw-primary)] text-white'
                : 'bg-white text-[var(--okw-text-muted)] hover:bg-[var(--okw-bg)]'
            }`}
          >
            {mode === 'both' ? (
              <>
                <Columns size={11} className="inline -mt-0.5 mr-1" />
                Side-by-Side
              </>
            ) : (
              mode.toUpperCase()
            )}
          </button>
        ))}
      </div>

      {/* Run / Stop */}
      {isRunning ? (
        <button
          onClick={onStop}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[var(--okw-accent)] text-white text-xs font-medium hover:opacity-90 transition-opacity"
        >
          <Square size={11} /> Stop
        </button>
      ) : (
        <button
          onClick={onRun}
          disabled={!canRun}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[var(--okw-primary)] text-white text-xs font-medium hover:bg-[var(--okw-primary-dark)] transition-colors disabled:opacity-50"
        >
          <Play size={13} />
          {selectedCount > 0 ? `Run ${selectedCount} Selected` : 'Run All'}
        </button>
      )}

      {/* Global timer */}
      {isRunning && (
        <span className="flex items-center gap-1 text-xs tabular-nums text-[var(--okw-warning)] font-medium animate-pulse">
          <Clock size={11} /> {globalElapsed}s
        </span>
      )}

      <div className="flex-1" />

      <button
        onClick={onUploadClick}
        disabled={isUploading}
        className="flex items-center gap-1 px-2 py-1.5 rounded-lg border border-[var(--okw-border)] text-xs font-medium text-[var(--okw-text)] hover:bg-white transition-colors disabled:opacity-50"
      >
        {isUploading ? <Loader2 size={12} className="animate-spin" /> : <Upload size={12} />}
        {isUploading ? 'Uploading...' : 'Upload Tests'}
      </button>
      <button
        onClick={onAddClick}
        className="flex items-center gap-1 px-2 py-1.5 rounded-lg border border-[var(--okw-border)] text-xs font-medium text-[var(--okw-text)] hover:bg-white transition-colors"
      >
        <Plus size={13} /> Add Test
      </button>
    </div>
  );
}
