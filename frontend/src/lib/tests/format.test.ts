import { describe, expect, it } from 'vitest';
import {
  buildUploadMessage,
  compareEngines,
  decisionStyle,
  formatSeconds,
  formatUsd,
} from './format';

describe('formatSeconds / formatUsd', () => {
  it('formats milliseconds as seconds with one decimal', () => {
    expect(formatSeconds(1234)).toBe('1.2');
    expect(formatSeconds(0)).toBe('0.0');
  });

  it('formats dollars with thousands separators and two decimals', () => {
    expect(formatUsd(1234.5)).toBe('$1,234.50');
    expect(formatUsd(undefined)).toBe('$0.00');
    expect(formatUsd('42')).toBe('$42.00');
  });
});

describe('decisionStyle', () => {
  it('returns colors for known decisions and falls back to SKIP', () => {
    expect(decisionStyle('PASS').text).toBe('var(--okw-success)');
    expect(decisionStyle('WHATEVER')).toEqual(decisionStyle('SKIP'));
  });
});

describe('compareEngines', () => {
  it('computes which engine was faster and by how much', () => {
    const c = compareEngines(10_000, 500);
    expect(c.faster).toBe('code');
    expect(c.ratio).toBe(20);
    expect(c.llmSec).toBe(10);
    expect(c.codeSec).toBe(0.5);
  });

  it('guards against division by zero', () => {
    expect(compareEngines(1000, 0).ratio).toBe(1000);
  });

  it('compares total / total_pass from both summaries', () => {
    expect(
      compareEngines(1, 2, { total: 3, total_pass: 2 }, { total: 3, total_pass: 2 }).resultsMatch,
    ).toBe(true);
    expect(
      compareEngines(1, 2, { total: 3, total_pass: 2 }, { total: 3, total_pass: 3 }).resultsMatch,
    ).toBe(false);
    expect(compareEngines(1, 2).resultsMatch).toBe(true);
  });
});

describe('buildUploadMessage', () => {
  it('includes the file name, extension and data row count (excluding the header)', () => {
    const csv = 'name,age\nalice,30\nbob,40\n\n';
    const msg = buildUploadMessage('Cases.CSV', csv);
    expect(msg).toContain('**File:** Cases.CSV (csv)');
    expect(msg).toContain('**Rows:** ~2 data rows');
    expect(msg).toContain('```\n' + csv + '\n```');
  });

  it('truncates very large files', () => {
    const big = 'x'.repeat(6000);
    const msg = buildUploadMessage('big.jsonl', big);
    expect(msg).toContain('x'.repeat(5000) + '\n... (truncated)');
    expect(msg).not.toContain('x'.repeat(5001));
  });
});
