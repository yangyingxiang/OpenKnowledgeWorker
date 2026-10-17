'use client';

import { useRef, useState } from 'react';
import { api } from '@/lib/api';
import { useSSE } from '@/lib/useSSE';
import {
  emptyExecState,
  reduceExecEvent,
  type ExecState,
  type RunMode,
} from '@/lib/tests/execState';

/**
 * Runs test cases via the streaming `/tests/run` endpoint and folds the SSE events into
 * `ExecState` (see `reduceExecEvent`). Per-engine durations are measured client-side from
 * each test's `test_start` event.
 */
export function useTestRunner(processId: string, onAllDone: () => void) {
  const [exec, setExec] = useState<ExecState>(emptyExecState);
  const testRunner = useSSE();

  /* ----- timers ----- */
  const llmStartRef = useRef<Record<string, number>>({});
  const codeStartRef = useRef<Record<string, number>>({});

  const runTests = (mode: RunMode, caseIds?: string[]) => {
    // Single reset — one render instead of 11.
    setExec(emptyExecState);
    llmStartRef.current = {};
    codeStartRef.current = {};

    testRunner.startStream(
      () => api.runTests(processId, { mode, test_case_ids: caseIds }),
      (event) => {
        if (event.type === 'all_done') {
          onAllDone();
          return;
        }

        const tcId = event.test_case_id as string | undefined;
        if (!tcId) return;

        let elapsedMs = 0;
        if (event.type === 'test_start') {
          llmStartRef.current[tcId] = Date.now();
          codeStartRef.current[tcId] = Date.now();
        } else if (event.type === 'llm_result') {
          elapsedMs = Date.now() - (llmStartRef.current[tcId] ?? Date.now());
        } else if (event.type === 'code_result') {
          elapsedMs = Date.now() - (codeStartRef.current[tcId] ?? Date.now());
        }

        setExec((prev) => reduceExecEvent(prev, event, elapsedMs));
      },
    );
  };

  /** Show the execution of a test case that already has live results. */
  const selectTest = (tcId: string) => setExec((prev) => ({ ...prev, activeTestId: tcId }));

  return {
    exec,
    runTests,
    selectTest,
    stopTests: testRunner.stopStream,
    isRunning: testRunner.isStreaming,
  };
}
