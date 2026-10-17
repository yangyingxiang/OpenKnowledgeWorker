'use client';

import {
  AlertCircle,
  CheckCircle2,
  Code2,
  Download,
  Loader2,
  RefreshCw,
  RotateCcw,
  Settings2,
  TestTube2,
  XCircle,
  type LucideIcon,
} from 'lucide-react';
import type { CodeProject } from '@/lib/api';

/** Label / color / icon for each coding-agent phase (keys match the backend `status` values). */
const PHASE_CONFIG: Record<string, { label: string; color: string; icon: LucideIcon }> = {
  planning: { label: 'Planning', color: '#6366f1', icon: Settings2 },
  coding: { label: 'Coding', color: '#f59e0b', icon: Code2 },
  testing: { label: 'Testing', color: '#3b82f6', icon: TestTube2 },
  fixing: { label: 'Fixing', color: '#ef4444', icon: RotateCcw },
  complete: { label: 'Complete', color: '#22c55e', icon: CheckCircle2 },
  error: { label: 'Error', color: '#ef4444', icon: XCircle },
};

export interface TestOutputSummary {
  passed: number;
  failed: number;
  errors: number;
  output: string;
}

/** Top bar of the Code page: refresh, agent phase, test counts, project picker and download. */
export function CodeToolbar({
  onRefresh,
  agentPhase,
  isStreaming,
  iteration,
  testOutput,
  projects,
  activeProjectId,
  onSelectProject,
  downloadUrl,
}: {
  onRefresh: () => void;
  agentPhase: string;
  isStreaming: boolean;
  iteration: number | undefined;
  testOutput: TestOutputSummary | null;
  projects: CodeProject[];
  activeProjectId: string | undefined;
  onSelectProject: (projectId: string) => void;
  downloadUrl: string | null;
}) {
  const phaseInfo = PHASE_CONFIG[agentPhase] || PHASE_CONFIG.planning;
  const PhaseIcon = phaseInfo.icon;

  return (
    <div className="px-4 py-2.5 border-b border-[var(--okw-border)] bg-[var(--okw-bg)] flex items-center gap-2">
      <button
        onClick={onRefresh}
        className="p-1.5 rounded hover:bg-white transition-colors"
        title="Refresh"
      >
        <RefreshCw size={14} className="text-[var(--okw-text-muted)]" />
      </button>

      {/* Phase indicator */}
      {agentPhase && (
        <div
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium"
          style={{ backgroundColor: phaseInfo.color + '18', color: phaseInfo.color }}
        >
          {isStreaming ? <Loader2 size={12} className="animate-spin" /> : <PhaseIcon size={12} />}
          {phaseInfo.label}
          {iteration ? ` (iter ${iteration})` : ''}
        </div>
      )}

      {/* Test summary badge */}
      {testOutput && (
        <div className="flex items-center gap-1.5 text-xs">
          {testOutput.passed > 0 && (
            <span className="flex items-center gap-0.5 text-green-600">
              <CheckCircle2 size={12} /> {testOutput.passed}
            </span>
          )}
          {testOutput.failed > 0 && (
            <span className="flex items-center gap-0.5 text-red-500">
              <XCircle size={12} /> {testOutput.failed}
            </span>
          )}
          {testOutput.errors > 0 && (
            <span className="flex items-center gap-0.5 text-orange-500">
              <AlertCircle size={12} /> {testOutput.errors}
            </span>
          )}
        </div>
      )}

      <div className="flex-1" />

      {/* Project selector */}
      {projects.length > 0 && (
        <select
          className="text-xs border border-[var(--okw-border)] rounded px-2 py-1 bg-white"
          value={activeProjectId || ''}
          onChange={(e) => {
            const pid = e.target.value;
            if (!pid) return;
            onSelectProject(pid);
          }}
        >
          {projects.map((p) => (
            <option key={p.id} value={p.id}>
              Run {p.id.slice(0, 8)} — {p.status}
            </option>
          ))}
        </select>
      )}

      {downloadUrl && (
        <a
          href={downloadUrl}
          className="flex items-center gap-1 px-2 py-1 rounded text-xs text-[var(--okw-text-muted)] hover:bg-white transition-colors"
        >
          <Download size={12} /> Download ZIP
        </a>
      )}
    </div>
  );
}
