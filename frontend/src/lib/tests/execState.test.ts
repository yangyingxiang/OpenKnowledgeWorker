import { describe, expect, it } from 'vitest';
import {
  emptyExecState,
  reduceExecEvent,
  selectDisplayTestId,
  type ExecState,
  type TestRunEvent,
  type TraceStep,
} from './execState';

const step = (id: string): TraceStep => ({
  step_id: id,
  title: `Step ${id}`,
  decision: 'PASS',
  result_value: null,
});

function run(events: TestRunEvent[], elapsed = 0): ExecState {
  return events.reduce((s, e) => reduceExecEvent(s, e, elapsed), emptyExecState);
}

describe('reduceExecEvent', () => {
  it('ignores events without a test_case_id and unknown event types', () => {
    expect(reduceExecEvent(emptyExecState, { type: 'test_start' })).toBe(emptyExecState);
    expect(reduceExecEvent(emptyExecState, { type: 'mystery', test_case_id: 't1' })).toBe(
      emptyExecState,
    );
  });

  it('marks a test running and active on test_start', () => {
    const s = run([{ type: 'test_start', test_case_id: 't1', run_id: 'r1' }]);
    expect(s.activeTestId).toBe('t1');
    expect(s.liveTests.t1).toEqual({ status: 'running', runId: 'r1' });
  });

  it('accumulates llm_delta text per test case', () => {
    const s = run([
      { type: 'llm_delta', test_case_id: 't1', text: 'Hel' },
      { type: 'llm_delta', test_case_id: 't1', text: 'lo' },
      { type: 'llm_delta', test_case_id: 't2', text: 'x' },
    ]);
    expect(s.llmTexts).toEqual({ t1: 'Hello', t2: 'x' });
  });

  it('records llm_result steps, summary and the measured duration', () => {
    const result = { trace_steps: [step('a')], summary: { total: 2 } };
    const s = run(
      [
        { type: 'test_start', test_case_id: 't1' },
        { type: 'llm_result', test_case_id: 't1', result },
      ],
      1500,
    );
    expect(s.llmSteps.t1).toEqual([step('a')]);
    expect(s.llmSummaries.t1).toEqual({ total: 2 });
    expect(s.llmDurations.t1).toBe(1500);
    expect(s.liveTests.t1.llmResult).toBe(result);
    expect(s.liveTests.t1.status).toBe('running');
  });

  it('appends code_step events and lets code_result override them', () => {
    let s = run([
      { type: 'code_step', test_case_id: 't1', step: step('a') },
      { type: 'code_step', test_case_id: 't1', step: step('b') },
    ]);
    expect(s.codeSteps.t1.map((x) => x.step_id)).toEqual(['a', 'b']);

    s = reduceExecEvent(
      s,
      {
        type: 'code_result',
        test_case_id: 't1',
        result: { trace_steps: [step('c')], summary: {}, error: 'boom' },
      },
      20,
    );
    expect(s.codeSteps.t1.map((x) => x.step_id)).toEqual(['c']);
    expect(s.codeErrors.t1).toBe('boom');
    expect(s.codeDurations.t1).toBe(20);
  });

  it('keeps streamed code steps when code_result has no trace_steps', () => {
    const s = run([
      { type: 'code_step', test_case_id: 't1', step: step('a') },
      { type: 'code_result', test_case_id: 't1', result: { summary: {} } },
    ]);
    expect(s.codeSteps.t1.map((x) => x.step_id)).toEqual(['a']);
  });

  it('marks tests done or errored', () => {
    const s = run([
      { type: 'test_start', test_case_id: 't1' },
      {
        type: 'test_complete',
        test_case_id: 't1',
        assertions_passed: 3,
        assertions_total: 4,
        duration_ms: 900,
      },
      { type: 'error', test_case_id: 't2', error: 'bad input' },
    ]);
    expect(s.liveTests.t1).toMatchObject({ status: 'done', passed: 3, total: 4, durationMs: 900 });
    expect(s.liveTests.t2).toEqual({ status: 'error', error: 'bad input' });
  });
});

describe('selectDisplayTestId', () => {
  it('prefers the active test, then the first finished one', () => {
    expect(selectDisplayTestId(emptyExecState)).toBeNull();
    const done: ExecState = {
      ...emptyExecState,
      liveTests: { t1: { status: 'running' }, t2: { status: 'done' } },
    };
    expect(selectDisplayTestId(done)).toBe('t2');
    expect(selectDisplayTestId({ ...done, activeTestId: 't1' })).toBe('t1');
  });
});
