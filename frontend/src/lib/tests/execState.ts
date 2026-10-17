/**
 * Types and a pure reducer for live test-run execution state.
 *
 * The test runner streams SSE events (see backend `/tests/run`). Each event is folded into an
 * `ExecState` by `reduceExecEvent`, keyed by test case id, so the UI can show live progress for
 * the LLM-guided engine and the generated-code engine side by side.
 */

export interface TraceStep {
  step_id: string;
  title: string;
  decision: 'PASS' | 'FLAG' | 'EXCLUDE' | 'SKIP' | string;
  result_value: string | number | boolean | null;
  result_label?: string;
  rule_citation?: string;
  rationale?: string;
  method?: string;
  inputs?: Record<string, unknown>;
}

export interface TestResult {
  trace_steps: TraceStep[];
  summary: Record<string, unknown>;
}

export interface LiveTestState {
  status: 'pending' | 'running' | 'done' | 'error';
  llmResult?: TestResult;
  codeResult?: TestResult;
  passed?: number;
  total?: number;
  durationMs?: number;
  error?: string;
  runId?: string;
}

export type RunMode = 'llm' | 'code' | 'both';

/** All live execution state, consolidated into one object to reduce render cascades. */
export interface ExecState {
  liveTests: Record<string, LiveTestState>;
  llmSteps: Record<string, TraceStep[]>;
  codeSteps: Record<string, TraceStep[]>;
  llmDurations: Record<string, number>;
  codeDurations: Record<string, number>;
  llmErrors: Record<string, string>;
  codeErrors: Record<string, string>;
  llmTexts: Record<string, string>;
  llmSummaries: Record<string, Record<string, unknown>>;
  codeSummaries: Record<string, Record<string, unknown>>;
  activeTestId: string | null;
}

export const emptyExecState: ExecState = {
  liveTests: {},
  llmSteps: {},
  codeSteps: {},
  llmDurations: {},
  codeDurations: {},
  llmErrors: {},
  codeErrors: {},
  llmTexts: {},
  llmSummaries: {},
  codeSummaries: {},
  activeTestId: null,
};

export interface TestRunEvent {
  type: string;
  [key: string]: unknown;
}

/**
 * Fold one test-run SSE event into the execution state.
 *
 * @param elapsedMs for `llm_result` / `code_result`: wall-clock time since that test's
 *   `test_start`, measured by the caller (keeps this function pure).
 * @returns the same object when the event doesn't change anything.
 */
export function reduceExecEvent(
  prev: ExecState,
  event: TestRunEvent,
  elapsedMs: number = 0,
): ExecState {
  const tcId = event.test_case_id as string | undefined;
  if (!tcId) return prev;

  switch (event.type) {
    case 'test_start':
      return {
        ...prev,
        activeTestId: tcId,
        liveTests: {
          ...prev.liveTests,
          [tcId]: { status: 'running', runId: event.run_id as string | undefined },
        },
      };

    case 'llm_delta': {
      const chunk = event.text as string | undefined;
      if (!chunk) return prev;
      return {
        ...prev,
        llmTexts: {
          ...prev.llmTexts,
          [tcId]: (prev.llmTexts[tcId] ?? '') + chunk,
        },
      };
    }

    case 'llm_result': {
      const result = event.result as TestResult | undefined;
      if (!result) return prev;
      return {
        ...prev,
        llmSteps: { ...prev.llmSteps, [tcId]: result.trace_steps ?? [] },
        llmDurations: { ...prev.llmDurations, [tcId]: elapsedMs },
        llmSummaries: { ...prev.llmSummaries, [tcId]: result.summary ?? {} },
        liveTests: {
          ...prev.liveTests,
          [tcId]: { ...prev.liveTests[tcId], llmResult: result },
        },
      };
    }

    case 'code_step': {
      const step = event.step as TraceStep | undefined;
      if (!step) return prev;
      return {
        ...prev,
        codeSteps: {
          ...prev.codeSteps,
          [tcId]: [...(prev.codeSteps[tcId] ?? []), step],
        },
      };
    }

    case 'code_result': {
      const result = event.result as (TestResult & { error?: string }) | undefined;
      if (!result) return prev;
      return {
        ...prev,
        codeErrors: result.error ? { ...prev.codeErrors, [tcId]: result.error } : prev.codeErrors,
        codeSteps: {
          ...prev.codeSteps,
          [tcId]: result.trace_steps ?? prev.codeSteps[tcId] ?? [],
        },
        codeDurations: { ...prev.codeDurations, [tcId]: elapsedMs },
        codeSummaries: { ...prev.codeSummaries, [tcId]: result.summary ?? {} },
        liveTests: {
          ...prev.liveTests,
          [tcId]: { ...prev.liveTests[tcId], codeResult: result },
        },
      };
    }

    case 'test_complete':
      return {
        ...prev,
        liveTests: {
          ...prev.liveTests,
          [tcId]: {
            ...prev.liveTests[tcId],
            status: 'done',
            passed: event.assertions_passed as number | undefined,
            total: event.assertions_total as number | undefined,
            durationMs: event.duration_ms as number | undefined,
          },
        },
      };

    case 'error':
      return {
        ...prev,
        liveTests: {
          ...prev.liveTests,
          [tcId]: {
            ...prev.liveTests[tcId],
            status: 'error',
            error: event.error as string | undefined,
          },
        },
      };

    default:
      return prev;
  }
}

/**
 * Which test case the execution area should show: the active one while running,
 * otherwise the first one that has finished.
 */
export function selectDisplayTestId(state: ExecState): string | null {
  return (
    state.activeTestId ??
    Object.keys(state.liveTests).find((id) => state.liveTests[id]?.status === 'done') ??
    null
  );
}
