/**
 * Pure helpers for showing "proposed change" diffs of the PDD in the SOP studio.
 */

export interface DiffLine {
  type: 'same' | 'added' | 'removed';
  text: string;
}

export type CondensedDiffLine = DiffLine | { type: 'separator' };

/** LCS-based line diff. Intended for small inputs (section-level diffs, usually <100 lines). */
export function lineDiff(aLines: string[], bLines: string[]): DiffLine[] {
  const n = aLines.length,
    m = bLines.length;
  if (n === 0) return bLines.map((t) => ({ type: 'added' as const, text: t }));
  if (m === 0) return aLines.map((t) => ({ type: 'removed' as const, text: t }));

  const dp: number[][] = Array.from({ length: n + 1 }, () => new Array(m + 1).fill(0));
  for (let i = 1; i <= n; i++)
    for (let j = 1; j <= m; j++)
      dp[i][j] =
        aLines[i - 1] === bLines[j - 1]
          ? dp[i - 1][j - 1] + 1
          : Math.max(dp[i - 1][j], dp[i][j - 1]);
  const result: DiffLine[] = [];
  let i = n,
    j = m;
  while (i > 0 || j > 0) {
    if (i > 0 && j > 0 && aLines[i - 1] === bLines[j - 1]) {
      result.unshift({ type: 'same', text: aLines[i - 1] });
      i--;
      j--;
    } else if (j > 0 && (i === 0 || dp[i][j - 1] >= dp[i - 1][j])) {
      result.unshift({ type: 'added', text: bLines[j - 1] });
      j--;
    } else {
      result.unshift({ type: 'removed', text: aLines[i - 1] });
      i--;
    }
  }
  return result;
}

/** Client-side section merge — mirrors backend _merge_section logic. */
export function mergeSection(fullContent: string, sectionPath: string, newContent: string): string {
  if (!fullContent.trim()) return newContent.trim();
  const key = sectionPath.toLowerCase().replace(/[_-]/g, ' ').trim();

  if (key === 'purpose') {
    const lines = fullContent.split('\n');
    const rest: string[] = [];
    let foundH2 = false;
    for (const line of lines) {
      if (line.startsWith('## ')) foundH2 = true;
      if (foundH2) rest.push(line);
    }
    return rest.length ? newContent.trimEnd() + '\n\n' + rest.join('\n') : newContent.trim();
  }

  if (sectionPath === 'full') return newContent.trim();

  // Find the section by matching ## headers
  const lines = fullContent.split('\n');
  const result: string[] = [];
  let inSection = false;
  let replaced = false;

  for (const line of lines) {
    if (!replaced && line.startsWith('## ') && !line.startsWith('### ')) {
      const hdr = line.slice(3).trim().toLowerCase().replace(/[_-]/g, ' ');
      if (hdr.includes(key) || key.includes(hdr.split(':')[0].trim())) {
        inSection = true;
        result.push(newContent.trimEnd());
        replaced = true;
        continue;
      }
      if (inSection) {
        inSection = false;
      }
    }
    if (!inSection) result.push(line);
  }
  if (!replaced) {
    result.push('');
    result.push(newContent.trimEnd());
  }
  return result.join('\n');
}

/** Extract only the lines belonging to a section from the PDD for focused diffing. */
export function extractSection(fullContent: string, sectionPath: string): string[] {
  if (sectionPath === 'full') return fullContent.split('\n');
  const key = sectionPath.toLowerCase().replace(/[_-]/g, ' ').trim();
  const lines = fullContent.split('\n');
  const sectionLines: string[] = [];
  let inSection = false;

  if (key === 'purpose') {
    for (const line of lines) {
      if (line.startsWith('## ')) break;
      sectionLines.push(line);
    }
    return sectionLines;
  }

  for (const line of lines) {
    if (line.startsWith('## ') && !line.startsWith('### ')) {
      const hdr = line.slice(3).trim().toLowerCase().replace(/[_-]/g, ' ');
      if (inSection) break;
      if (hdr.includes(key) || key.includes(hdr.split(':')[0].trim())) {
        inSection = true;
      }
    }
    if (inSection) sectionLines.push(line);
  }
  return sectionLines;
}

/** Keep only lines within `context` lines of a change; gaps become a single separator. */
export function condenseDiff(lines: DiffLine[], context = 3): CondensedDiffLine[] {
  const changeIdx = new Set<number>();
  lines.forEach((l, i) => {
    if (l.type !== 'same') changeIdx.add(i);
  });
  const visible = new Set<number>();
  for (const idx of changeIdx) {
    for (let k = Math.max(0, idx - context); k <= Math.min(lines.length - 1, idx + context); k++) {
      visible.add(k);
    }
  }
  const result: CondensedDiffLine[] = [];
  let lastIdx = -1;
  for (const idx of Array.from(visible).sort((a, b) => a - b)) {
    if (lastIdx >= 0 && idx - lastIdx > 1) {
      result.push({ type: 'separator' });
    }
    result.push(lines[idx]);
    lastIdx = idx;
  }
  return result;
}

export function hasChanges(diff: DiffLine[]): boolean {
  return diff.some((d) => d.type !== 'same');
}
