/** Pure display helpers for the Test Suite page. */

/** Milliseconds → seconds with one decimal, e.g. 1234 → "1.2". */
export function formatSeconds(ms: number): string {
  return (ms / 1000).toFixed(1);
}

/** Format a value as US dollars with exactly two decimals, e.g. 1234.5 → "$1,234.50". */
export function formatUsd(value: unknown): string {
  return `$${Number(value ?? 0).toLocaleString('en-US', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

/* ─── Decision colors ────────────────────────────────────────── */

export interface DecisionColors {
  bg: string;
  text: string;
  border: string;
}

const DECISION_COLORS: Record<string, DecisionColors> = {
  PASS: { bg: 'rgba(34,197,94,0.10)', text: 'var(--okw-success)', border: 'var(--okw-success)' },
  FLAG: { bg: 'rgba(245,158,11,0.10)', text: 'var(--okw-warning)', border: 'var(--okw-warning)' },
  EXCLUDE: { bg: 'rgba(239,68,68,0.10)', text: 'var(--okw-accent)', border: 'var(--okw-accent)' },
  SKIP: {
    bg: 'rgba(148,163,184,0.12)',
    text: 'var(--okw-text-muted)',
    border: 'var(--okw-text-muted)',
  },
  INFO: { bg: 'rgba(99,102,241,0.10)', text: '#6366f1', border: '#6366f1' },
};

/** Colors for a trace-step decision badge; unknown decisions fall back to SKIP styling. */
export function decisionStyle(decision: string): DecisionColors {
  return DECISION_COLORS[decision] ?? DECISION_COLORS.SKIP;
}

/* ─── Engine comparison ──────────────────────────────────────── */

export interface EngineComparison {
  llmSec: number;
  codeSec: number;
  faster: 'llm' | 'code';
  /** How many times faster the faster engine was. */
  ratio: number;
  /** Whether both engines reported the same total / total_pass counts. */
  resultsMatch: boolean;
}

export function compareEngines(
  llmDurationMs: number,
  codeDurationMs: number,
  llmSummary?: Record<string, unknown>,
  codeSummary?: Record<string, unknown>,
): EngineComparison {
  const llmSec = llmDurationMs / 1000;
  const codeSec = codeDurationMs / 1000;

  const faster = codeSec < llmSec ? 'code' : 'llm';
  const ratio =
    faster === 'code' ? llmSec / Math.max(codeSec, 0.001) : codeSec / Math.max(llmSec, 0.001);

  const llmTotal = (llmSummary?.total as number) ?? 0;
  const codeTotal = (codeSummary?.total as number) ?? 0;
  const llmPass = (llmSummary?.total_pass as number) ?? 0;
  const codePass = (codeSummary?.total_pass as number) ?? 0;
  const resultsMatch = llmTotal === codeTotal && llmPass === codePass;

  return { llmSec, codeSec, faster, ratio, resultsMatch };
}

/* ─── Bulk upload ────────────────────────────────────────────── */

const UPLOAD_PREVIEW_CHARS = 5000;

/**
 * Build the chat message sent to the agent when the user uploads a CSV / JSONL test file.
 * The agent analyzes the structure and creates test cases from it.
 */
export function buildUploadMessage(fileName: string, text: string): string {
  const ext = fileName.split('.').pop()?.toLowerCase();
  return [
    `I've uploaded a test data file. Please analyze its structure, transform the data into our expected test case format, and create the test cases. Ask me any questions if the mapping is unclear.`,
    ``,
    `**File:** ${fileName} (${ext})`,
    `**Rows:** ~${text.split('\n').filter((l) => l.trim()).length - 1} data rows`,
    ``,
    '```',
    text.length > UPLOAD_PREVIEW_CHARS
      ? text.slice(0, UPLOAD_PREVIEW_CHARS) + '\n... (truncated)'
      : text,
    '```',
  ].join('\n');
}
