import { describe, expect, it } from 'vitest';
import { classifyLine, formatFileSize, groupBlocks, mimeIcon, parseText } from './parseText';

describe('classifyLine', () => {
  it('detects blank lines, key-value pairs and plain text', () => {
    expect(classifyLine('   ').type).toBe('blank');
    expect(classifyLine('Applicant Name: Jane Doe')).toMatchObject({
      type: 'key-value',
      key: 'Applicant Name',
      value: 'Jane Doe',
    });
    expect(classifyLine('This is a normal sentence.').type).toBe('text');
  });

  it('detects pipe tables, separator rows and tab-separated rows', () => {
    expect(classifyLine('| a | b |')).toMatchObject({ type: 'table-row', cells: ['a', 'b'] });
    expect(classifyLine('|---|:-:|').type).toBe('table-separator');
    expect(classifyLine('one\ttwo\tthree')).toMatchObject({
      type: 'table-row',
      cells: ['one', 'two', 'three'],
    });
    expect(classifyLine('one\ttwo').type).not.toBe('table-row');
  });

  it('detects ALL CAPS headings and headings underlined with dashes', () => {
    expect(classifyLine('INCOME DETAILS').type).toBe('section-header');
    expect(classifyLine('Income details', '-----').type).toBe('section-header');
    expect(classifyLine('-----').type).toBe('table-separator');
  });
});

describe('parseText / groupBlocks', () => {
  it('groups consecutive table rows and key-value pairs', () => {
    const text = [
      'SUMMARY',
      'Name: Jane',
      'Age: 40',
      '',
      '| a | b |',
      '|---|---|',
      '| 1 | 2 |',
    ].join('\n');
    const blocks = groupBlocks(parseText(text));
    expect(blocks.map((b) => [b.type, b.items.length])).toEqual([
      ['section-header', 1],
      ['kv-group', 2],
      ['blank', 1],
      ['table', 3],
    ]);
  });
});

describe('document format helpers', () => {
  it('formats file sizes', () => {
    expect(formatFileSize(512)).toBe('512 B');
    expect(formatFileSize(1536)).toBe('1.5 KB');
    expect(formatFileSize(3 * 1024 * 1024)).toBe('3.0 MB');
  });

  it('picks an icon by MIME type', () => {
    expect(mimeIcon('application/pdf')).toBe('📄');
    expect(mimeIcon('text/html')).toBe('🌐');
    expect(mimeIcon('text/markdown')).toBe('📝');
  });
});
