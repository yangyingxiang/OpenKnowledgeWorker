import { describe, expect, it } from 'vitest';
import { condenseDiff, extractSection, hasChanges, lineDiff, mergeSection } from './diff';

const DOC = [
  '# Title',
  'Purpose text.',
  '## Key Concepts',
  'concept A',
  '## Business Rules',
  'rule 1',
].join('\n');

describe('lineDiff', () => {
  it('marks added, removed and unchanged lines', () => {
    expect(lineDiff(['a', 'b', 'c'], ['a', 'x', 'c'])).toEqual([
      { type: 'same', text: 'a' },
      { type: 'removed', text: 'b' },
      { type: 'added', text: 'x' },
      { type: 'same', text: 'c' },
    ]);
  });

  it('handles empty inputs', () => {
    expect(lineDiff([], ['a'])).toEqual([{ type: 'added', text: 'a' }]);
    expect(lineDiff(['a'], [])).toEqual([{ type: 'removed', text: 'a' }]);
  });

  it('hasChanges is false for identical inputs', () => {
    expect(hasChanges(lineDiff(['a', 'b'], ['a', 'b']))).toBe(false);
    expect(hasChanges(lineDiff(['a'], ['b']))).toBe(true);
  });
});

describe('extractSection', () => {
  it('extracts a ## section by fuzzy name', () => {
    expect(extractSection(DOC, 'key_concepts')).toEqual(['## Key Concepts', 'concept A']);
  });

  it('extracts the purpose (everything before the first ## header)', () => {
    expect(extractSection(DOC, 'purpose')).toEqual(['# Title', 'Purpose text.']);
  });
});

describe('mergeSection', () => {
  it('replaces an existing section in place', () => {
    const merged = mergeSection(DOC, 'business-rules', '## Business Rules\nrule 2');
    expect(merged).toBe(
      [
        '# Title',
        'Purpose text.',
        '## Key Concepts',
        'concept A',
        '## Business Rules',
        'rule 2',
      ].join('\n'),
    );
  });

  it('appends a section that does not exist yet', () => {
    expect(mergeSection(DOC, 'outputs', '## Outputs\nnone')).toBe(DOC + '\n\n## Outputs\nnone');
  });

  it('replaces the purpose while keeping all ## sections', () => {
    expect(mergeSection(DOC, 'purpose', '# New\nNew purpose.')).toBe(
      '# New\nNew purpose.\n\n## Key Concepts\nconcept A\n## Business Rules\nrule 1',
    );
  });
});

describe('condenseDiff', () => {
  it('keeps context lines around changes and inserts separators for gaps', () => {
    const a = Array.from({ length: 20 }, (_, i) => `line ${i}`);
    const b = [...a];
    b[1] = 'changed 1';
    b[18] = 'changed 18';
    const condensed = condenseDiff(lineDiff(a, b), 1);
    const separators = condensed.filter((l) => l.type === 'separator');
    expect(separators).toHaveLength(1);
    expect(condensed[0]).toEqual({ type: 'same', text: 'line 0' });
    expect(condensed.length).toBeLessThan(lineDiff(a, b).length);
  });
});
