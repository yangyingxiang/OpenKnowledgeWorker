import { describe, expect, it } from 'vitest';
import {
  countPdlBlocks,
  countSteps,
  groupPhases,
  isEarlyExit,
  isParallelPhase,
  parsePddContent,
  parsePdlToBlocks,
  stepNumbersWithPdl,
  type PddPhase,
  type PddStep,
} from './parse';

const SAMPLE_PDD = `# Income Verification — Process Decision Document

Determine a household's monthly income
for benefit eligibility.

## Key Concepts

| Term | Definition |
|------|------------|
| Household | People who live and eat together |
| Earned income | Wages and **salary** |

## Variable Reference

| Variable | Type | Description |
|---|---|---|
| applicant_age | int | Age in years |

## Process

### Phase 1: Intake

Collect the application.

#### Step 1.1: Check age

Verify the applicant is an adult.

Second paragraph.

<!-- pdl
GIVEN applicant_age
IF applicant_age < 18
  RETURN "ineligible"
-->

#### Step 1.2: Record household

Write down household members.

### Phase 2: Income Calculation

#### Step 2.1: Sum wages

Add up all wages.

## Business Rules

| Rule | Description |
|---|---|
| BR-1 | Minors are ineligible |

## Decision Priority

| # | Rule |
|---|---|
| 1 | Age check first |
`;

function step(partial: Partial<PddStep>): PddStep {
  return { number: '1.1', title: '', description: '', pdl: null, ...partial };
}

function phase(partial: Partial<PddPhase>): PddPhase {
  return { number: 1, title: '', description: '', steps: [], ...partial };
}

describe('parsePddContent', () => {
  it('returns null for empty or very short content', () => {
    expect(parsePddContent('')).toBeNull();
    expect(parsePddContent('# Hi')).toBeNull();
  });

  it('returns null when there is neither a title nor phases', () => {
    expect(parsePddContent('Just some prose that is long enough to parse.')).toBeNull();
  });

  it('extracts the title (without the document-type suffix) and purpose', () => {
    const parsed = parsePddContent(SAMPLE_PDD)!;
    expect(parsed.title).toBe('Income Verification');
    expect(parsed.purpose).toBe("Determine a household's monthly income for benefit eligibility.");
  });

  it('strips both "Definition" and legacy "Decision" title suffixes', () => {
    for (const suffix of ['Process Definition Document', 'Process Decision Document']) {
      const parsed = parsePddContent(SAMPLE_PDD.replace('Process Decision Document', suffix))!;
      expect(parsed.title).toBe('Income Verification');
    }
  });

  it('parses markdown tables into rows keyed by header', () => {
    const parsed = parsePddContent(SAMPLE_PDD)!;
    expect(parsed.keyConcepts).toEqual([
      { Term: 'Household', Definition: 'People who live and eat together' },
      { Term: 'Earned income', Definition: 'Wages and **salary**' },
    ]);
    expect(parsed.variables).toEqual([
      { Variable: 'applicant_age', Type: 'int', Description: 'Age in years' },
    ]);
    expect(parsed.businessRules).toEqual([{ Rule: 'BR-1', Description: 'Minors are ineligible' }]);
    expect(parsed.decisionPriority).toEqual([{ '#': '1', Rule: 'Age check first' }]);
  });

  it('parses phases, steps, descriptions and PDL blocks', () => {
    const parsed = parsePddContent(SAMPLE_PDD)!;
    expect(parsed.phases.map((p) => [p.number, p.title])).toEqual([
      [1, 'Intake'],
      [2, 'Income Calculation'],
    ]);

    const [s11, s12] = parsed.phases[0].steps;
    expect(s11.number).toBe('1.1');
    expect(s11.title).toBe('Check age');
    expect(s11.description).toBe('Verify the applicant is an adult.\n\nSecond paragraph.');
    expect(s11.pdl).toBe('GIVEN applicant_age\nIF applicant_age < 18\n  RETURN "ineligible"');
    expect(s12.pdl).toBeNull();
    expect(parsed.phases[1].steps[0].title).toBe('Sum wages');
  });

  it('accepts headers without the "Phase"/"Step" words', () => {
    const md = '# Title here\n\n## 1. First\n\n#### 1.1 Do it\n\nBody';
    const parsed = parsePddContent(md)!;
    expect(parsed.phases[0].title).toBe('First');
    expect(parsed.phases[0].steps[0]).toMatchObject({ number: '1.1', title: 'Do it' });
  });
});

describe('PDD counting helpers', () => {
  it('counts steps and PDL blocks', () => {
    const parsed = parsePddContent(SAMPLE_PDD)!;
    expect(countSteps(parsed)).toBe(3);
    expect(countPdlBlocks(parsed)).toBe(1);
    expect(stepNumbersWithPdl(parsed)).toEqual(['1.1']);
  });
});

describe('isEarlyExit', () => {
  it('detects ineligibility in the title or description', () => {
    expect(isEarlyExit(step({ title: 'Mark applicant Ineligible' }))).toBe(true);
    expect(isEarlyExit(step({ description: 'Applicant is categorically barred' }))).toBe(true);
  });

  it('detects exclusion / ineligible returns in PDL', () => {
    expect(isEarlyExit(step({ pdl: 'RETURN "excluded"' }))).toBe(true);
    expect(isEarlyExit(step({ pdl: 'SET status = EXCLUDE' }))).toBe(true);
  });

  it('is false for ordinary steps', () => {
    expect(isEarlyExit(step({ title: 'Sum wages', pdl: 'RETURN total' }))).toBe(false);
  });
});

describe('groupPhases', () => {
  it('merges consecutive parallel phases and keeps others separate', () => {
    const phases = [
      phase({ number: 1, title: 'Intake' }),
      phase({ number: 2, title: 'Wage Income Calculation' }),
      phase({ number: 3, title: 'Parallel checks' }),
      phase({ number: 4, title: 'Decision' }),
      phase({ number: 5, title: 'Parallel follow-ups' }),
    ];
    expect(isParallelPhase(phases[1])).toBe(true);
    expect(isParallelPhase(phases[0])).toBe(false);
    expect(groupPhases(phases).map((g) => [g.type, g.phases.map((p) => p.number)])).toEqual([
      ['single', [1]],
      ['parallel', [2, 3]],
      ['single', [4]],
      ['parallel', [5]],
    ]);
  });
});

describe('parsePdlToBlocks', () => {
  it('classifies statements by keyword and computes indent from leading spaces', () => {
    const pdl = [
      'GIVEN income',
      'FOR EACH stream IN streams',
      '  IF stream.amount > 0',
      '    SET total = total + 1',
      '  ELSE IF stream.flag',
      '  ELSE',
      '',
      'DECIDE eligibility',
      'RETURN total',
      'something else',
    ].join('\n');
    expect(parsePdlToBlocks(pdl).map((b) => [b.type, b.indent])).toEqual([
      ['given', 0],
      ['foreach', 0],
      ['if', 1],
      ['set', 2],
      ['if', 1],
      ['else', 1],
      ['decide', 0],
      ['return', 0],
      ['set', 0],
    ]);
  });
});
