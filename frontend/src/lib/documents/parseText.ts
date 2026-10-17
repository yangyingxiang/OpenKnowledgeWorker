/**
 * Pure helpers that turn a document's extracted plain text into typed lines and blocks
 * so it can be rendered as a styled, print-like page (see components/documents/DocumentRenderer).
 */

export interface ParsedLine {
  type: 'section-header' | 'key-value' | 'table-row' | 'table-separator' | 'blank' | 'text';
  raw: string;
  key?: string;
  value?: string;
  cells?: string[];
}

/** Classify one line of text. `nextLine` is used to detect headings underlined with ---/===. */
export function classifyLine(line: string, nextLine?: string): ParsedLine {
  const trimmed = line.trim();

  // Blank line
  if (trimmed === '') return { type: 'blank', raw: line };

  // Table row: contains | separators with content
  if (trimmed.includes('|') && trimmed.startsWith('|') && trimmed.endsWith('|')) {
    const cells = trimmed
      .slice(1, -1)
      .split('|')
      .map((c) => c.trim());
    // Check if this is a separator row (all cells are dashes)
    if (cells.every((c) => /^[-=:]+$/.test(c) || c === '')) {
      return { type: 'table-separator', raw: line, cells };
    }
    return { type: 'table-row', raw: line, cells };
  }

  // Tab-separated data (3+ columns)
  if (line.includes('\t')) {
    const cells = line
      .split('\t')
      .map((c) => c.trim())
      .filter(Boolean);
    if (cells.length >= 3) {
      return { type: 'table-row', raw: line, cells };
    }
  }

  // Section header: ALL CAPS line (at least 3 chars, no lowercase), or line followed by ---- or ====
  const isAllCaps =
    trimmed.length >= 3 && /^[A-Z0-9\s,./&()\-:]+$/.test(trimmed) && /[A-Z]{2,}/.test(trimmed);
  const isFollowedByDashes = nextLine !== undefined && /^[-=]{3,}\s*$/.test(nextLine.trim());
  if (isAllCaps || isFollowedByDashes) {
    return { type: 'section-header', raw: line };
  }

  // Separator-only line (dashes/equals used as a divider, e.g. under a heading)
  if (/^[-=]{3,}\s*$/.test(trimmed)) {
    return { type: 'table-separator', raw: line };
  }

  // Key-value pair: "Label: value" or "Label : value"
  const kvMatch = trimmed.match(/^([A-Za-z0-9\s/()#.\-_&]{2,50}?)\s*:\s+(.+)$/);
  if (kvMatch) {
    return { type: 'key-value', raw: line, key: kvMatch[1].trim(), value: kvMatch[2].trim() };
  }

  return { type: 'text', raw: line };
}

export function parseText(text: string): ParsedLine[] {
  const lines = text.split('\n');
  return lines.map((line, i) => classifyLine(line, lines[i + 1]));
}

export interface LineBlock {
  /** 'table' | 'kv-group' | any other ParsedLine type */
  type: string;
  items: ParsedLine[];
}

/** Group consecutive table rows together and consecutive key-value pairs together. */
export function groupBlocks(parsed: ParsedLine[]): LineBlock[] {
  const result: LineBlock[] = [];
  let current: LineBlock | null = null;

  for (const line of parsed) {
    const groupType =
      line.type === 'table-row' || line.type === 'table-separator'
        ? 'table'
        : line.type === 'key-value'
          ? 'kv-group'
          : line.type;

    if (current && current.type === groupType) {
      current.items.push(line);
    } else {
      if (current) result.push(current);
      current = { type: groupType, items: [line] };
    }
  }
  if (current) result.push(current);
  return result;
}

/** Human-readable file size, e.g. 1536 → "1.5 KB". */
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** Emoji icon for a document's MIME type. */
export function mimeIcon(mime: string): string {
  if (mime.includes('pdf')) return '📄';
  if (mime.includes('html')) return '🌐';
  return '📝';
}
