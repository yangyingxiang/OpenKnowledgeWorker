/**
 * Pure parsing helpers for the Process Definition Document (PDD / SOP) markdown.
 *
 * The PDD is a markdown document with a fixed-ish structure:
 *
 *   # <Title> — Process Definition Document
 *   <purpose paragraph>
 *   ## Key Concepts | Variable Reference | Outputs   (markdown tables)
 *   ## Process
 *   ### Phase 1: <title>
 *   #### Step 1.1: <title>
 *   <description>
 *   <!-- pdl
 *   <Process Decision Logic pseudo-code>
 *   -->
 *   ## Business Rules | Decision Priority            (markdown tables)
 *
 * Nothing in this module touches React or the DOM so it can be unit tested directly.
 */

export type Row = Record<string, string>;

export interface PddStep {
  number: string;
  title: string;
  description: string;
  pdl: string | null;
}

export interface PddPhase {
  number: number;
  title: string;
  description: string;
  steps: PddStep[];
}

export interface ParsedPdd {
  title: string;
  purpose: string;
  keyConcepts: Row[];
  variables: Row[];
  outputs: Row[];
  phases: PddPhase[];
  businessRules: Row[];
  decisionPriority: Row[];
}

/** Keys of ParsedPdd that hold table rows (and can be expanded as accordion sections). */
export type PddTableSection =
  'keyConcepts' | 'variables' | 'outputs' | 'businessRules' | 'decisionPriority';

export const PDD_TABLE_SECTIONS: PddTableSection[] = [
  'keyConcepts',
  'variables',
  'outputs',
  'businessRules',
  'decisionPriority',
];

/** Parse PDD markdown into a structured document. Returns null when it doesn't look like a PDD. */
export function parsePddContent(md: string): ParsedPdd | null {
  if (!md || md.trim().length < 20) return null;

  const r: ParsedPdd = {
    title: '',
    purpose: '',
    keyConcepts: [],
    variables: [],
    outputs: [],
    phases: [],
    businessRules: [],
    decisionPriority: [],
  };

  const lines = md.split('\n');
  let section = '';
  let phase: PddPhase | null = null;
  let step: PddStep | null = null;
  let inPdl = false;
  let pdlBuf = '';
  let descBuf = '';
  let purposeBuf = '';
  let tHeaders: string[] = [];
  let tRows: Row[] = [];
  let inTable = false;

  const flushStep = () => {
    if (step && descBuf.trim()) step.description = descBuf.trim();
    descBuf = '';
  };
  const flushPhase = () => {
    if (phase && !step && descBuf.trim()) phase.description = descBuf.trim();
    descBuf = '';
  };
  const flushTable = () => {
    if (!inTable || !tRows.length) {
      tRows = [];
      tHeaders = [];
      inTable = false;
      return;
    }
    const map: Record<string, Row[]> = {
      keyConcepts: r.keyConcepts,
      variables: r.variables,
      outputs: r.outputs,
      businessRules: r.businessRules,
      decisionPriority: r.decisionPriority,
    };
    const target = map[section];
    if (target) target.push(...tRows);
    tRows = [];
    tHeaders = [];
    inTable = false;
  };

  for (const line of lines) {
    // PDL blocks
    if (line.trim().startsWith('<!-- pdl')) {
      inPdl = true;
      pdlBuf = '';
      continue;
    }
    if (inPdl) {
      if (line.trim() === '-->') {
        inPdl = false;
        if (step) step.pdl = pdlBuf.trim();
      } else pdlBuf += line + '\n';
      continue;
    }

    // Title
    if (line.startsWith('# ') && !line.startsWith('## ') && !r.title) {
      r.title = line
        .replace(/^# /, '')
        .replace(/\s*[—–-]+\s*Process (?:Definition|Decision) Document$/i, '')
        .trim();
      section = 'purpose'; // Text after title is the purpose paragraph
      continue;
    }

    // Phase headers  ### Phase N: ...
    const pm = line.match(/^#{2,3}\s+(?:Phase\s+)?(\d+)[:\s—–.\-]+\s*(.+)$/);
    if (pm && !line.startsWith('####')) {
      flushStep();
      flushTable();
      section = 'process';
      phase = { number: +pm[1], title: pm[2].trim(), description: '', steps: [] };
      r.phases.push(phase);
      step = null;
      descBuf = '';
      continue;
    }

    // Step headers  #### Step N.M: ...
    const sm = line.match(/^#{3,4}\s+(?:Step\s+)?(\d+\.\d+)[:\s—–.\-]+\s*(.+)$/);
    if (sm && phase) {
      flushStep();
      step = { number: sm[1], title: sm[2].trim(), description: '', pdl: null };
      phase.steps.push(step);
      descBuf = '';
      continue;
    }

    // Section headers  ## ...
    if (line.startsWith('## ')) {
      flushStep();
      flushPhase();
      flushTable();
      if (section === 'purpose') r.purpose = purposeBuf.trim();
      const t = line.replace(/^## /, '').trim().toLowerCase();
      if (t.includes('purpose')) {
        section = 'purpose';
        purposeBuf = '';
      } else if (t.includes('key concept')) section = 'keyConcepts';
      else if (t.includes('variable ref')) section = 'variables';
      else if (t.includes('output')) section = 'outputs';
      else if (t.includes('process')) section = 'process';
      else if (t.includes('business rule')) section = 'businessRules';
      else if (t.includes('decision priority')) section = 'decisionPriority';
      else section = t;
      phase = null;
      step = null;
      continue;
    }

    // Tables
    if (line.trim().startsWith('|') && line.trim().endsWith('|')) {
      const cells = line
        .split('|')
        .slice(1, -1)
        .map((c) => c.trim());
      if (cells.every((c) => /^[-:]+$/.test(c))) continue;
      if (!inTable) {
        inTable = true;
        tHeaders = cells;
      } else {
        const row: Row = {};
        cells.forEach((c, i) => {
          row[tHeaders[i] || `col${i}`] = c;
        });
        tRows.push(row);
      }
      continue;
    }
    if (inTable && line.trim() === '') flushTable();

    // Content
    if (section === 'purpose' && line.trim()) {
      purposeBuf += (purposeBuf ? ' ' : '') + line.trim();
    } else if (step) {
      descBuf += line + '\n';
    } else if (phase && !step) {
      descBuf += line + '\n';
    }
  }

  flushStep();
  flushPhase();
  flushTable();
  if (section === 'purpose') r.purpose = purposeBuf.trim();
  if (r.phases.length === 0 && !r.title) return null;
  return r;
}

/* ─── Derived helpers ────────────────────────────────────────── */

export function countSteps(parsed: ParsedPdd): number {
  return parsed.phases.reduce((s, p) => s + p.steps.length, 0);
}

export function countPdlBlocks(parsed: ParsedPdd): number {
  return parsed.phases.reduce((s, p) => s + p.steps.filter((st) => st.pdl).length, 0);
}

/** Step numbers (e.g. "1.2") of every step that carries a PDL block. */
export function stepNumbersWithPdl(parsed: ParsedPdd): string[] {
  return parsed.phases.flatMap((p) => p.steps.filter((s) => s.pdl).map((s) => s.number));
}

/** Heuristic: does this step terminate the process early (ineligible / excluded)? */
export function isEarlyExit(step: PddStep): boolean {
  const t = (step.title + ' ' + step.description).toLowerCase();
  if (t.includes('ineligible') || t.includes('categorically barred')) return true;
  if (step.pdl) {
    const pdl = step.pdl.toLowerCase();
    if (pdl.includes('return') && (pdl.includes('ineligible') || pdl.includes('excluded')))
      return true;
    if (pdl.includes('exclude')) return true;
  }
  return false;
}

/** Heuristic: should this phase be drawn as parallel execution in the flow view? */
export function isParallelPhase(phase: PddPhase): boolean {
  // Only mark as parallel if the phase explicitly indicates parallel/concurrent execution
  const t = phase.title.toLowerCase();
  return t.includes('parallel') || (t.includes('income') && t.includes('calculation'));
}

export interface PhaseGroup {
  type: 'single' | 'parallel';
  phases: PddPhase[];
}

/** Group consecutive parallel phases together; every other phase forms its own group. */
export function groupPhases(phases: PddPhase[]): PhaseGroup[] {
  const groups: PhaseGroup[] = [];
  for (const phase of phases) {
    if (isParallelPhase(phase)) {
      const last = groups[groups.length - 1];
      if (last && last.type === 'parallel') {
        last.phases.push(phase);
      } else {
        groups.push({ type: 'parallel', phases: [phase] });
      }
    } else {
      groups.push({ type: 'single', phases: [phase] });
    }
  }
  return groups;
}

/* ─── PDL → logic-flow blocks ────────────────────────────────── */

export type PdlBlockType = 'set' | 'if' | 'return' | 'given' | 'decide' | 'else' | 'foreach';

export interface PdlBlock {
  type: PdlBlockType;
  text: string;
  indent: number;
}

/** Split PDL pseudo-code into one block per non-empty line, classified by leading keyword. */
export function parsePdlToBlocks(pdl: string): PdlBlock[] {
  const blocks: PdlBlock[] = [];
  for (const line of pdl.split('\n')) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    const indent = line.search(/\S/) / 2;
    if (/^GIVEN\b/i.test(trimmed)) blocks.push({ type: 'given', text: trimmed, indent });
    else if (/^DECIDE\b/i.test(trimmed)) blocks.push({ type: 'decide', text: trimmed, indent });
    else if (/^IF\b/i.test(trimmed) || /^ELSE\s+IF\b/i.test(trimmed))
      blocks.push({ type: 'if', text: trimmed, indent });
    else if (/^ELSE\b/i.test(trimmed)) blocks.push({ type: 'else', text: trimmed, indent });
    else if (/^SET\b/i.test(trimmed)) blocks.push({ type: 'set', text: trimmed, indent });
    else if (/^RETURN\b/i.test(trimmed)) blocks.push({ type: 'return', text: trimmed, indent });
    else if (/^FOR\s+EACH\b/i.test(trimmed))
      blocks.push({ type: 'foreach', text: trimmed, indent });
    else blocks.push({ type: 'set', text: trimmed, indent });
  }
  return blocks;
}
