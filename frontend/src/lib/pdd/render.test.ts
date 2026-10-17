import { describe, expect, it } from 'vitest';
import { escapeHtml, fallbackMarkdown, highlightPdl, renderDesc, renderInline } from './render';

describe('escapeHtml', () => {
  it('escapes &, < and >', () => {
    expect(escapeHtml('<a> & <b>')).toBe('&lt;a&gt; &amp; &lt;b&gt;');
  });
});

describe('renderInline', () => {
  it('renders bold, italic and code', () => {
    expect(renderInline('**bold** and *it*')).toBe('<strong>bold</strong> and <em>it</em>');
    expect(renderInline('use `x`')).toContain('>x</code>');
  });

  it('escapes HTML before adding markup', () => {
    expect(renderInline('<script>')).toBe('&lt;script&gt;');
  });

  it('renders source / tentative / confirmed badges', () => {
    const html = renderInline('[source: doc.pdf p3] [TENTATIVE] [CONFIRMED by SME]');
    expect(html).toContain('title="Source: doc.pdf p3">doc.pdf p3</span>');
    expect(html).toContain('>TENTATIVE</span>');
    expect(html).toContain('>CONFIRMED by SME</span>');
  });
});

describe('renderDesc', () => {
  it('splits blank-line separated paragraphs and joins wrapped lines', () => {
    const html = renderDesc('line one\nline two\n\nsecond');
    expect(html.match(/<p /g)).toHaveLength(2);
    expect(html).toContain('>line one line two</p>');
  });
});

describe('highlightPdl', () => {
  it('highlights keywords, strings and numbers', () => {
    const html = highlightPdl('IF age < 18 RETURN "minor"');
    expect(html).toContain('<span style="color:#c678dd;font-weight:bold">IF</span>');
    expect(html).toContain('&lt;');
    expect(html).toContain('<span style="color:#d19a66">18</span>');
    expect(html).toContain('"minor"</span>');
  });
});

describe('fallbackMarkdown', () => {
  it('renders headings, lists and tables', () => {
    const html = fallbackMarkdown('# Title\n\n- a\n- b\n\n| h1 | h2 |\n|---|---|\n| x | y |\n');
    expect(html).toContain('<h1>Title</h1>');
    expect(html).toContain('<ul><li>a</li>\n<li>b</li>\n</ul>');
    expect(html).toContain('<thead><tr><th>h1</th><th>h2</th></tr></thead>');
    expect(html).toContain('<tbody><tr><td>x</td><td>y</td></tr></tbody>');
  });
});
