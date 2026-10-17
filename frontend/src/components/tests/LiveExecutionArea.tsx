'use client';

import type { ExecState, RunMode } from '@/lib/tests/execState';
import { ComparisonBanner } from './ComparisonBanner';
import { ExecutionPanel } from './ExecutionPanel';
import { LlmStreamPanel } from './LlmStreamPanel';

/**
 * Live execution view for the currently displayed test case: the LLM panel, the code-engine
 * panel, or both side by side with a comparison banner — depending on the run mode.
 */
export function LiveExecutionArea({
  exec,
  displayTestId,
  testName,
  runMode,
}: {
  exec: ExecState;
  displayTestId: string | null;
  testName: string | undefined;
  runMode: RunMode;
}) {
  const currentLive = displayTestId ? exec.liveTests[displayTestId] : undefined;
  const currentCodeSteps = displayTestId ? (exec.codeSteps[displayTestId] ?? []) : [];
  const currentLlmText = displayTestId ? (exec.llmTexts[displayTestId] ?? '') : '';

  const llmRunning = currentLive?.status === 'running' && !currentLive?.llmResult;
  const codeRunning = currentLive?.status === 'running' && !currentLive?.codeResult;

  const bothDone =
    displayTestId &&
    exec.llmDurations[displayTestId] !== undefined &&
    exec.codeDurations[displayTestId] !== undefined;

  const llmPanel = (
    <LlmStreamPanel
      text={currentLlmText}
      isRunning={!!llmRunning}
      durationMs={displayTestId ? exec.llmDurations[displayTestId] : undefined}
      error={displayTestId ? exec.llmErrors[displayTestId] : undefined}
    />
  );
  const codePanel = (
    <ExecutionPanel
      label="Code Engine"
      steps={currentCodeSteps}
      isRunning={!!codeRunning}
      durationMs={displayTestId ? exec.codeDurations[displayTestId] : undefined}
      error={displayTestId ? exec.codeErrors[displayTestId] : undefined}
      summary={displayTestId ? exec.codeSummaries[displayTestId] : undefined}
    />
  );

  return (
    <div className="animate-[fadeSlideIn_0.3s_ease-out_both]">
      {/* Section heading */}
      {testName && (
        <div className="flex items-center gap-2 mb-2">
          <h3 className="text-sm font-semibold text-[var(--okw-text)]">Execution: {testName}</h3>
          {currentLive?.status === 'running' && (
            <span className="text-[10px] uppercase tracking-wider font-bold text-[var(--okw-warning)] animate-pulse">
              Live
            </span>
          )}
          {currentLive?.status === 'done' && (
            <span className="text-[10px] uppercase tracking-wider font-bold text-[var(--okw-success)]">
              Complete
            </span>
          )}
          {currentLive?.status === 'error' && (
            <span className="text-[10px] uppercase tracking-wider font-bold text-[var(--okw-accent)]">
              Error
            </span>
          )}
        </div>
      )}

      {/* Error display */}
      {currentLive?.status === 'error' && currentLive.error && (
        <div className="rounded-lg border border-[var(--okw-accent)] bg-red-50 px-3 py-2 mb-3">
          <p className="text-xs text-[var(--okw-accent)] font-medium">{currentLive.error}</p>
        </div>
      )}

      {/* Side-by-side vs. single panel */}
      {runMode === 'both' ? (
        <>
          <div className="flex gap-3">
            {llmPanel}
            {codePanel}
          </div>

          {/* Comparison summary */}
          {displayTestId && bothDone && (
            <ComparisonBanner
              llmDuration={exec.llmDurations[displayTestId]}
              codeDuration={exec.codeDurations[displayTestId]}
              llmSummary={exec.llmSummaries[displayTestId]}
              codeSummary={exec.codeSummaries[displayTestId]}
            />
          )}
        </>
      ) : runMode === 'llm' ? (
        /* LLM single panel — raw text */
        llmPanel
      ) : (
        /* Code single panel — trace step cards */
        codePanel
      )}
    </div>
  );
}
